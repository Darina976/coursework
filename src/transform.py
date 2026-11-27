"""
Модуль трансформации данных (Transform).
Очищает сырые CSV-данные из Data Lake и сохраняет результат в папку processed/.
"""

import logging
from datetime import datetime
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def find_latest_csv(lake_dir: Path) -> Path:
    """Находит самый свежий CSV-файл в папке Data Lake."""
    csv_files = list(lake_dir.rglob("*.csv"))
    if not csv_files:
        raise FileNotFoundError(f"В {lake_dir} не найдено CSV-файлов")
    return max(csv_files, key=lambda p: p.stat().st_mtime)


def clean_price(df: pd.DataFrame, price_col: str = 'price') -> pd.DataFrame:
    """Очищает поле цены: удаляет символы валют, пробелы, конвертирует в float."""
    if price_col not in df.columns:
        logger.warning(f"Колонка '{price_col}' не найдена. Пропускаем очистку цен.")
        return df

    logger.info(f"Очистка поля '{price_col}'...")
    original_count = len(df)

    s = df[price_col].astype(str).str.strip()
    # Удаляем всё, кроме цифр, точки и запятой
    s = s.str.replace(r'[^\d.,]', '', regex=True)
    # Если есть и точка, и запятая — запятая считается разделителем тысяч
    mask_both = s.str.contains(r'\.', na=False) & s.str.contains(r',', na=False)
    s = s.where(~mask_both, s.str.replace(',', '', regex=False))
    # Если осталась запятая — это десятичный разделитель
    s = s.str.replace(',', '.', regex=False)

    df[price_col] = pd.to_numeric(s, errors='coerce')
    df = df[df[price_col] > 0].copy()

    cleaned_count = df[price_col].notna().sum()
    logger.info(f"  Удалено строк с некорректной ценой: {original_count - cleaned_count}")
    return df


def clean_coordinates(df: pd.DataFrame, lat_col='latitude', lon_col='longitude') -> pd.DataFrame:
    """Валидирует геокоординаты Амстердама (если они есть в датасете)."""
    if lat_col not in df.columns or lon_col not in df.columns:
        logger.warning(
            f"Колонки координат ({lat_col}, {lon_col}) отсутствуют в датасете. "
            "Пропускаем валидацию."
        )
        return df

    logger.info("Валидация геокоординат...")
    original_len = len(df)

    df = df[
        (df[lat_col] >= 52.0) & (df[lat_col] <= 52.5) &
        (df[lon_col] >= 4.6) & (df[lon_col] <= 5.1)
    ].copy()

    logger.info(f"  Удалено строк с некорректными координатами: {original_len - len(df)}")
    return df


def normalize_room_type(df: pd.DataFrame, col='room_type') -> pd.DataFrame:
    """Нормализует справочник типов комнат."""
    if col not in df.columns:
        logger.warning(f"Колонка '{col}' не найдена. Пропускаем нормализацию.")
        return df

    logger.info(f"Нормализация поля '{col}'...")

    mapping = {
        'Entire home/apt': 'Entire home',
        'Private room': 'Private room',
        'Shared room': 'Shared room',
        'Hotel room': 'Hotel room',
    }

    df[col] = df[col].str.strip().map(mapping).fillna(df[col])
    return df


def handle_missing_values(df: pd.DataFrame) -> pd.DataFrame:
    """Обрабатывает пропуски в ключевых полях."""
    logger.info("Обработка пропусков...")

    if 'neighbourhood_group' in df.columns:
        df['neighbourhood_group'] = df['neighbourhood_group'].fillna('Unknown')

    if 'number_of_reviews' in df.columns:
        df['number_of_reviews'] = df['number_of_reviews'].fillna(0).astype(int)

    required_cols = ['id', 'price']
    existing_required = [c for c in required_cols if c in df.columns]
    df = df.dropna(subset=existing_required)

    logger.info(f"  Строк после обработки пропусков: {len(df)}")
    return df


def add_derived_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Добавляет вычисляемые поля."""
    logger.info("Добавление вычисляемых полей...")

    df['scrape_date'] = datetime.utcnow().strftime('%Y-%m-%d')

    if 'last_review' in df.columns:
        df['last_review'] = pd.to_datetime(df['last_review'], errors='coerce')

    if 'reviews_per_month' in df.columns:
        df['reviews_per_month'] = df['reviews_per_month'].round(2)

    return df


def transform_listings() -> str:
    """Основная функция трансформации."""
    lake_dir = Path("data/lake")
    processed_dir = Path("data/processed")
    processed_dir.mkdir(parents=True, exist_ok=True)

    logger.info("=== Начало этапа Transform ===")

    source_file = find_latest_csv(lake_dir)
    logger.info(f"Исходный файл: {source_file.name}")

    df = pd.read_csv(source_file, low_memory=False)
    logger.info(f"Загружено строк: {len(df)}, колонок: {len(df.columns)}")

    df = clean_price(df)
    df = clean_coordinates(df)
    df = normalize_room_type(df)
    df = handle_missing_values(df)
    df = add_derived_columns(df)

    output_file = processed_dir / f"listings_clean_{datetime.utcnow().strftime('%Y%m%d')}.csv"
    df.to_csv(output_file, index=False, encoding='utf-8')

    size_mb = output_file.stat().st_size / (1024 * 1024)
    logger.info(f"Очищенный файл сохранён: {output_file.name}")
    logger.info(f"  Строк: {len(df)}, Размер: {size_mb:.2f} МБ")
    logger.info("=== Этап Transform успешно завершён ===")

    return str(output_file)


if __name__ == "__main__":
    try:
        result = transform_listings()
        print(f"\n✅ Успешно! Очищенные данные: {result}")
    except Exception as e:
        logger.error(f"Ошибка при трансформации: {e}", exc_info=True)
        raise