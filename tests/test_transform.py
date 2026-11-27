import pandas as pd

from src.transform import (
    clean_price,
    clean_coordinates,
    normalize_room_type,
    handle_missing_values,
)


class TestCleanPrice:
    def test_removes_currency_symbols(self):
        df = pd.DataFrame({"price": ["$1,200.50", "€800", "1000"]})
        result = clean_price(df)
        assert result["price"].iloc[0] == 1200.50
        assert result["price"].iloc[1] == 800.0
        assert result["price"].iloc[2] == 1000.0

    def test_removes_invalid_rows(self):
        df = pd.DataFrame({"price": ["abc", "-100", "500"]})
        result = clean_price(df)
        assert len(result) == 1
        assert result["price"].iloc[0] == 500.0

    def test_handles_missing_column(self):
        df = pd.DataFrame({"other": [1, 2]})
        result = clean_price(df)
        assert "price" not in result.columns


class TestCleanCoordinates:
    def test_filters_outside_amsterdam(self):
        df = pd.DataFrame({
            "latitude": [52.37, 40.71, 52.10],
            "longitude": [4.89, -74.00, 5.05],
        })
        result = clean_coordinates(df)
        assert len(result) == 2

    def test_skips_if_no_columns(self):
        df = pd.DataFrame({"id": [1, 2]})
        result = clean_coordinates(df)
        assert len(result) == 2


class TestNormalizeRoomType:
    def test_maps_entire_home(self):
        df = pd.DataFrame({"room_type": ["Entire home/apt", "Private room"]})
        result = normalize_room_type(df)
        assert result["room_type"].iloc[0] == "Entire home"


class TestHandleMissingValues:
    def test_fills_neighbourhood_group(self):
        df = pd.DataFrame({
            "id": [1, 2],
            "price": [100.0, 200.0],
            "neighbourhood_group": [None, "Centrum"],
            "number_of_reviews": [None, 5],
        })
        result = handle_missing_values(df)
        assert result["neighbourhood_group"].iloc[0] == "Unknown"
        assert result["number_of_reviews"].iloc[0] == 0