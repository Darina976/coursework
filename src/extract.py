"""
Модуль извлечения данных (Extract).
Автоматически находит CSV-файл в data/raw и копирует его в Data Lake (Bronze layer).
Data Lake реализован на локальной файловой системе (MinIO недоступен в РФ).
"""

import logging
import shutil
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def extract_listings() -> str:
    """
    Находит первый попавшийся CSV-файл в data/raw и копирует его в data/lake.
    """
    raw_dir = Path("data/raw")

    if not raw_dir.exists():
        raise FileNotFoundError(f"Папка {raw_dir.absolute()} не существует.")

    csv_files = list(raw_dir.rglob("*.csv")) + list(raw_dir.rglob("*.csv.gz"))

    if not csv_files:
        raise FileNotFoundError(
            f"В папке {raw_dir.absolute()} не найдено ни одного CSV-файла. "
            "Пожалуйста, распакуйте датасет в data/raw/"
        )

    source_file = csv_files[0]
    logger.info(f"Найден исходный файл: {source_file.name}")

    scrape_date = datetime.utcnow().strftime("%Y-%m-%d")
    lake_dir = Path(f"data/lake/listings/{scrape_date}")
    lake_dir.mkdir(parents=True, exist_ok=True)

    target_file = lake_dir / source_file.name

    logger.info("=== Начало этапа Extract ===")
    logger.info("Источник: локальный файл (Kaggle / InsideAirbnb Amsterdam)")
    logger.info(f"Целевой путь в Data Lake: {target_file.absolute()}")

    shutil.copy2(source_file, target_file)

    size_mb = target_file.stat().st_size / (1024 * 1024)
    logger.info(f"Файл успешно скопирован в Data Lake. Размер: {size_mb:.2f} МБ")
    logger.info("=== Этап Extract успешно завершён ===")

    return str(target_file)


if __name__ == "__main__":
    try:
        result = extract_listings()
        print(f"\n✅ Успешно! Сырые данные сохранены в Data Lake: {result}")
    except Exception as e:
        logger.error(f"Ошибка при извлечении данных: {e}", exc_info=True)
        raise