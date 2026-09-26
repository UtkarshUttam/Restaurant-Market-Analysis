"""Input and output helpers for the restaurant dataset."""

from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DATA_PATH = PROJECT_ROOT / "data" / "raw" / "restaurant_data.csv"
PROCESSED_DATA_PATH = PROJECT_ROOT / "data" / "processed" / "restaurants_clean.csv"
CUISINE_DATA_PATH = PROJECT_ROOT / "data" / "processed" / "restaurant_cuisines.csv"


def load_raw_data(path: str | Path = RAW_DATA_PATH) -> pd.DataFrame:
    """Load the source CSV while correctly handling its UTF-8 BOM."""
    source = Path(path)
    if not source.exists():
        raise FileNotFoundError(f"Dataset not found: {source}")
    return pd.read_csv(source, encoding="utf-8-sig")


def load_processed_data(path: str | Path = PROCESSED_DATA_PATH) -> pd.DataFrame:
    """Load a previously generated, restaurant-level dataset."""
    source = Path(path)
    if not source.exists():
        raise FileNotFoundError(
            f"Processed data not found: {source}. Run `python -m src.data_cleaning` first."
        )
    return pd.read_csv(source)