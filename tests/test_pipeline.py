import pandas as pd
from pathlib import Path


def test_extract_creates_file_in_lake(tmp_path, monkeypatch):
    """Проверяет, что extract копирует CSV в data/lake."""
    raw = tmp_path / "data" / "raw"
    raw.mkdir(parents=True)
    df = pd.DataFrame({"id": [1], "price": ["100"]})
    df.to_csv(raw / "test.csv", index=False)

    monkeypatch.chdir(tmp_path)
    from src.extract import extract_listings

    result = extract_listings()
    assert Path(result).exists()
    assert "lake" in result


def test_transform_produces_clean_csv(tmp_path, monkeypatch):
    """Проверяет, что transform создаёт очищенный CSV."""
    lake = tmp_path / "data" / "lake" / "listings" / "2026-11-27"
    lake.mkdir(parents=True)
    df = pd.DataFrame({
        "id": [1, 2],
        "price": ["$100", "$200"],
        "room_type": ["Entire home/apt", "Private room"],
        "number_of_reviews": [5, 3],
        "neighbourhood_group": ["Centrum", None],
    })
    df.to_csv(lake / "listings.csv", index=False)

    monkeypatch.chdir(tmp_path)
    from src.transform import transform_listings

    result = transform_listings()
    cleaned = pd.read_csv(result)
    assert "price" in cleaned.columns
    assert cleaned["price"].iloc[0] == 100.0