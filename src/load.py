"""
Модуль загрузки данных (Load).
Загружает очищенные CSV-данные в PostgreSQL с использованием UPSERT (идемпотентность).
Адаптирован под структуру датасета Inside Airbnb Amsterdam (Kaggle).
"""

import logging
import os
import socket
from datetime import datetime
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_db_engine():
    """Создаёт подключение к PostgreSQL с автоподменой хоста."""
    user = os.getenv("POSTGRES_USER", "airbnb_user")
    password = os.getenv("POSTGRES_PASSWORD", "airbnb_secure_pass")
    host = os.getenv("POSTGRES_HOST", "postgres")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "airbnb_dwh")

    # Автоподмена: если хост не резолвится (например, "postgres" вне Docker),
    # используем localhost
    try:
        socket.gethostbyname(host)
    except socket.gaierror:
        logger.warning(f"Хост '{host}' не резолвится. Используем 'localhost'.")
        host = "localhost"

    connection_string = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}"
    return create_engine(connection_string)


def find_latest_processed_csv(processed_dir: Path) -> Path:
    """Находит последний очищенный CSV-файл."""
    csv_files = list(processed_dir.glob("*.csv"))
    if not csv_files:
        raise FileNotFoundError(f"В папке {processed_dir} нет очищенных CSV-файлов.")
    return max(csv_files, key=lambda p: p.stat().st_mtime)


def upsert_dimensions(df: pd.DataFrame, conn) -> None:
    """Загружает уникальные значения в таблицы измерений (dim_*)."""
    logger.info("Загрузка измерений (dim_*)...")

    # 1. dim_location (Районы)
    if 'neighbourhood_cleansed' in df.columns:
        loc_df = df[['neighbourhood_cleansed']].drop_duplicates()
        loc_df['neighbourhood_cleansed'] = loc_df['neighbourhood_cleansed'].fillna('Unknown')
        loaded = 0
        for _, row in loc_df.iterrows():
            conn.execute(
                text("""
                    INSERT INTO dim_location (neighbourhood, neighbourhood_group)
                    VALUES (:neighbourhood, :neighbourhood_group)
                    ON CONFLICT (neighbourhood) DO NOTHING;
                """),
                {"neighbourhood": row['neighbourhood_cleansed'],
                 "neighbourhood_group": 'Amsterdam'}
            )
            loaded += 1
        logger.info(f"  Загружено районов: {loaded}")
    else:
        logger.warning("  Колонка 'neighbourhood_cleansed' отсутствует. Пропускаем dim_location.")

    # 2. dim_host (Хосты)
    if 'host_id' in df.columns:
        host_cols = ['host_id']
        if 'host_is_superhost' in df.columns:
            host_cols.append('host_is_superhost')
        host_df = df[host_cols].dropna(subset=['host_id']).drop_duplicates(subset=['host_id'])

        for _, row in host_df.iterrows():
            is_super = False
            if 'host_is_superhost' in host_df.columns:
                val = str(row['host_is_superhost']).lower()
                is_super = val in ['true', 't', '1', 'yes', 'y']
            conn.execute(
                text("""
                    INSERT INTO dim_host (host_id, host_name, is_superhost)
                    VALUES (:host_id, :host_name, :is_superhost)
                    ON CONFLICT (host_id) DO UPDATE
                    SET is_superhost = EXCLUDED.is_superhost;
                """),
                {"host_id": int(row['host_id']), "host_name": 'Unknown',
                 "is_superhost": is_super}
            )
        logger.info(f"  Загружено хостов: {len(host_df)}")
    else:
        logger.warning("  Колонка 'host_id' отсутствует. Пропускаем dim_host.")

    # 3. dim_property (Типы жилья)
    if 'room_type' in df.columns:
        prop_df = df[['room_type']].dropna().drop_duplicates()
        prop_df['property_type'] = 'Unknown'
        for _, row in prop_df.iterrows():
            conn.execute(
                text("""
                    INSERT INTO dim_property (room_type, property_type)
                    VALUES (:room_type, :property_type)
                    ON CONFLICT (room_type) DO UPDATE
                    SET property_type = EXCLUDED.property_type;
                """),
                {"room_type": row['room_type'],
                 "property_type": row['property_type']}
            )
        logger.info(f"  Загружено типов жилья: {len(prop_df)}")
    else:
        logger.warning("  Колонка 'room_type' отсутствует. Пропускаем dim_property.")


def upsert_facts(df: pd.DataFrame, conn) -> None:
    """Загружает факты в fact_listings с использованием UPSERT."""
    logger.info("Загрузка фактов (fact_listings)...")

    facts_loaded = 0
    scrape_date = datetime.utcnow().strftime('%Y-%m-%d')

    if 'id' not in df.columns:
        logger.error("Не найдена колонка с ID объекта (id)")
        return

    for _, row in df.iterrows():
        listing_id = int(row['id'])
        price = float(row['price']) if pd.notna(row.get('price')) else 0.0
        neighbourhood = (
            str(row['neighbourhood_cleansed'])
            if pd.notna(row.get('neighbourhood_cleansed'))
            else 'Unknown'
        )
        room_type = (
            str(row['room_type']) if pd.notna(row.get('room_type')) else 'Unknown'
        )
        host_id = int(row['host_id']) if pd.notna(row.get('host_id')) else None
        minimum_nights = (
            int(row['minimum_nights']) if pd.notna(row.get('minimum_nights')) else 1
        )
        number_of_reviews = (
            int(row['number_of_reviews']) if pd.notna(row.get('number_of_reviews')) else 0
        )

        # Проверка существования хоста (защита от нарушения FK)
        if host_id is not None:
            exists = conn.execute(
                text("SELECT 1 FROM dim_host WHERE host_id = :h"), {"h": host_id}
            ).fetchone()
            if not exists:
                host_id = None

        location_id = None
        if neighbourhood != 'Unknown':
            r = conn.execute(
                text("SELECT location_id FROM dim_location WHERE neighbourhood = :n"),
                {"n": neighbourhood}
            ).fetchone()
            if r:
                location_id = r[0]

        property_id = None
        if room_type != 'Unknown':
            r = conn.execute(
                text("SELECT property_id FROM dim_property WHERE room_type = :r"),
                {"r": room_type}
            ).fetchone()
            if r:
                property_id = r[0]

        conn.execute(
            text("""
                INSERT INTO fact_listings
                (listing_id, scrape_date, location_id, host_id, property_id,
                 name, price_eur, minimum_nights, number_of_reviews)
                VALUES
                (:listing_id, :scrape_date, :location_id, :host_id, :property_id,
                 :name, :price, :min_nights, :reviews)
                ON CONFLICT (listing_id, scrape_date) DO UPDATE
                SET price_eur = EXCLUDED.price_eur,
                    number_of_reviews = EXCLUDED.number_of_reviews;
            """),
            {
                "listing_id": listing_id,
                "scrape_date": scrape_date,
                "location_id": location_id,
                "host_id": host_id,
                "property_id": property_id,
                "name": f"Listing {listing_id}",
                "price": price,
                "min_nights": minimum_nights,
                "reviews": number_of_reviews,
            }
        )
        facts_loaded += 1

    logger.info(f"  Загружено фактов (объектов): {facts_loaded}")


def load_listings() -> None:
    """Основная функция загрузки."""
    processed_dir = Path("data/processed")

    logger.info("=== Начало этапа Load ===")

    source_file = find_latest_processed_csv(processed_dir)
    logger.info(f"Исходный файл: {source_file.name}")

    df = pd.read_csv(source_file, low_memory=False)
    logger.info(f"Прочитано строк для загрузки: {len(df)}")

    engine = get_db_engine()

    with engine.connect() as conn:
        try:
            upsert_dimensions(df, conn)
            upsert_facts(df, conn)
            conn.commit()
            logger.info("Транзакция успешно завершена (commit).")
        except Exception as e:
            conn.rollback()
            logger.error(f"Ошибка загрузки, выполнен откат: {e}")
            raise

    logger.info("=== Этап Load успешно завершён ===")


if __name__ == "__main__":
    try:
        load_listings()
        print("\n✅ Успешно! Данные загружены в PostgreSQL.")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}", exc_info=True)
        raise