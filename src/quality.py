"""
Модуль контроля качества данных (Great Expectations).
Валидирует очищенный CSV перед загрузкой в DWH.
"""

import logging
from pathlib import Path

import pandas as pd
import great_expectations as gx
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def find_latest_processed_csv(processed_dir: Path) -> Path:
    csv_files = list(processed_dir.glob("*.csv"))
    if not csv_files:
        raise FileNotFoundError(f"В {processed_dir} нет очищенных CSV.")
    return max(csv_files, key=lambda p: p.stat().st_mtime)


def validate_listings() -> bool:
    """Запускает проверки Great Expectations для очищенных данных."""
    processed_dir = Path("data/processed")
    source_file = find_latest_processed_csv(processed_dir)
    logger.info(f"Валидация файла: {source_file.name}")

    df = pd.read_csv(source_file, low_memory=False)
    logger.info(f"Загружено строк для валидации: {len(df)}")

    context = gx.get_context(mode="ephemeral")

    source = context.sources.add_pandas("airbnb_listings_source")
    asset = source.add_dataframe_asset(name="listings_asset")
    batch_request = asset.build_batch_request(dataframe=df)
    validator = context.get_validator(batch_request=batch_request)

    results = []

    # 1. ID не должен быть пустым
    results.append(validator.expect_column_values_to_not_be_null("id"))

    # 2. Цена должна быть положительной
    results.append(
        validator.expect_column_values_to_be_between(
            "price", min_value=0.01, max_value=100000
        )
    )

    # 3. Количество отзывов не может быть отрицательным
    if "number_of_reviews" in df.columns:
        results.append(
            validator.expect_column_values_to_be_between(
                "number_of_reviews", min_value=0
            )
        )

    # 4. Тип комнаты должен быть из ожидаемого справочника
    if "room_type" in df.columns:
        expected_room_types = [
            "Entire home", "Private room", "Shared room", "Hotel room"
        ]
        results.append(
            validator.expect_column_values_to_be_in_set(
                "room_type", value_set=expected_room_types
            )
        )

    # 5. Минимальное количество ночей > 0
    if "minimum_nights" in df.columns:
        results.append(
            validator.expect_column_values_to_be_between(
                "minimum_nights", min_value=1, max_value=365
            )
        )

    failed = [r for r in results if not r.success]
    for r in results:
        status = "✅" if r.success else "❌"
        exp_type = r.expectation_config.expectation_type
        logger.info(f"  {status} {exp_type}")

    if failed:
        logger.error(f"Провалено проверок: {len(failed)} из {len(results)}")
        return False

    logger.info(f"Все {len(results)} проверок пройдены успешно.")
    return True


if __name__ == "__main__":
    success = validate_listings()
    if success:
        print("\n✅ Качество данных подтверждено.")
    else:
        print("\n⚠️ Обнаружены проблемы качества. Проверьте лог.")