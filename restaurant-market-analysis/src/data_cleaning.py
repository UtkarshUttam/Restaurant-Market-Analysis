"""Auditable cleaning and quality reporting for the source restaurant data."""

import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

from src.data_loader import PROJECT_ROOT, RAW_DATA_PATH, load_raw_data
from src.feature_engineering import add_features, explode_cuisines

FLAG_COLUMNS = {
    "has_table_booking",
    "has_online_delivery",
    "is_delivering_now",
    "switch_to_order_menu",
}
NUMERIC_COLUMNS = [
    "country_code",
    "longitude",
    "latitude",
    "average_cost_for_two",
    "price_range",
    "aggregate_rating",
    "votes",
]


def to_snake_case(value: str) -> str:
    """Convert source column labels into stable snake_case names."""
    value = re.sub(r"[^A-Za-z0-9]+", "_", value.strip())
    return re.sub(r"_+", "_", value).strip("_").lower()


def profile_data(frame: pd.DataFrame) -> dict[str, object]:
    """Return source-level diagnostics without changing or dropping records."""
    data = frame.copy()
    data.columns = [to_snake_case(column) for column in data.columns]
    cost = pd.to_numeric(data["average_cost_for_two"], errors="coerce")
    outlier_summary: dict[str, dict[str, int | float]] = {}
    for currency, group in data.groupby("currency", dropna=False):
        values = pd.to_numeric(group["average_cost_for_two"], errors="coerce").dropna()
        values = values.loc[values.gt(0)]
        q1, q3 = values.quantile([0.25, 0.75])
        spread = q3 - q1
        outlier_summary[str(currency)] = {
            "rows": int(len(values)),
            "iqr_lower_fence": float(q1 - 1.5 * spread),
            "iqr_upper_fence": float(q3 + 1.5 * spread),
            "flagged_rows": int((values > q3 + 1.5 * spread).sum()),
        }
    rating = pd.to_numeric(data["aggregate_rating"], errors="coerce")
    rating = rating.loc[rating.gt(0)]
    votes = pd.to_numeric(data["votes"], errors="coerce").dropna()

    def iqr_report(values: pd.Series) -> dict[str, int | float]:
        q1, q3 = values.quantile([0.25, 0.75])
        spread = q3 - q1
        lower, upper = q1 - 1.5 * spread, q3 + 1.5 * spread
        return {"rows": int(len(values)), "iqr_lower_fence": float(lower),
                "iqr_upper_fence": float(upper),
                "flagged_rows": int((values.lt(lower) | values.gt(upper)).sum())}
    return {
        "rows": int(len(data)),
        "columns": int(len(data.columns)),
        "column_names": list(data.columns),
        "dtypes": {key: str(value) for key, value in data.dtypes.items()},
        "missing_by_column": {
            key: int(value) for key, value in data.isna().sum().items()
        },
        "exact_duplicate_rows": int(data.duplicated().sum()),
        "duplicate_restaurant_ids": int(data["restaurant_id"].duplicated().sum()),
        "unique_restaurant_ids": int(data["restaurant_id"].nunique()),
        "invalid_coordinate_rows": int(
            (~data["longitude"].between(-180, 180)
             | ~data["latitude"].between(-90, 90)
             | ((data["longitude"] == 0) & (data["latitude"] == 0))).sum()
        ),
        "zero_cost_rows": int((cost == 0).sum()),
        "negative_cost_rows": int((cost < 0).sum()),
        "unrated_rows": int((pd.to_numeric(data["aggregate_rating"], errors="coerce") == 0).sum()),
        "invalid_ratings": int((~pd.to_numeric(data["aggregate_rating"], errors="coerce").between(0, 5)).sum()),
        "invalid_price_ranges": int((~pd.to_numeric(data["price_range"], errors="coerce").isin([1, 2, 3, 4])).sum()),
        "negative_votes": int((pd.to_numeric(data["votes"], errors="coerce") < 0).sum()),
        "cost_outliers_by_currency": outlier_summary,
        "numeric_outlier_summary": {
            "aggregate_rating_rated_only": iqr_report(rating),
            "votes": iqr_report(votes),
        },
        "country_currency_mappings": {
            str(code): sorted(group["currency"].dropna().unique().tolist())
            for code, group in data.groupby("country_code")
        },
        "rating_text_mismatches_for_zero_ratings": int(
            ((pd.to_numeric(data["aggregate_rating"], errors="coerce") == 0)
             != data["rating_text"].eq("Not rated")).sum()
        ),
        "service_flag_values": {
            column: sorted(data[column].dropna().astype(str).unique().tolist())
            for column in ["has_table_booking", "has_online_delivery", "is_delivering_now", "switch_to_order_menu"]
        },
        "currency_counts": {
            str(key): int(value)
            for key, value in data["currency"].value_counts(dropna=False).items()
        },
    }


def clean_data(frame: pd.DataFrame) -> pd.DataFrame:
    """Standardize labels/types, retain valid observations, and add features."""
    data = frame.copy()
    data.columns = [to_snake_case(column) for column in data.columns]

    for column in data.select_dtypes(include=["object", "string"]).columns:
        data[column] = data[column].map(
            lambda value: value.strip() if isinstance(value, str) else value
        )
        data[column] = data[column].replace("", pd.NA)

    for column in FLAG_COLUMNS:
        normalized = data[column].astype("string").str.strip().str.casefold()
        data[column] = normalized.map({"yes": "Yes", "no": "No"}).fillna(pd.NA)

    for column in NUMERIC_COLUMNS:
        data[column] = pd.to_numeric(data[column], errors="coerce")

    data.loc[~data["aggregate_rating"].between(0, 5), "aggregate_rating"] = np.nan
    data.loc[~data["price_range"].isin([1, 2, 3, 4]), "price_range"] = np.nan
    data.loc[data["votes"].lt(0), "votes"] = np.nan
    data.loc[data["average_cost_for_two"].lt(0), "average_cost_for_two"] = np.nan

    # The source uses (0, 0) for unknown coordinates; keep the restaurant row.
    zero_pair = data["longitude"].eq(0) & data["latitude"].eq(0)
    data.loc[zero_pair, ["longitude", "latitude"]] = np.nan
    invalid_longitude = ~data["longitude"].between(-180, 180)
    invalid_latitude = ~data["latitude"].between(-90, 90)
    data.loc[invalid_longitude, "longitude"] = np.nan
    data.loc[invalid_latitude, "latitude"] = np.nan

    return add_features(data)


def run_pipeline(
    raw_path: str | Path = RAW_DATA_PATH,
    output_dir: str | Path = PROJECT_ROOT / "data" / "processed",
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, object]]:
    """Create cleaned restaurant and cuisine datasets plus a quality report."""
    raw = load_raw_data(raw_path)
    report = profile_data(raw)
    cleaned = clean_data(raw)
    cuisines = explode_cuisines(cleaned)

    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    cleaned.to_csv(destination / "restaurants_clean.csv", index=False)
    cuisines.to_csv(destination / "restaurant_cuisines.csv", index=False)
    (destination / "data_quality_report.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    return cleaned, cuisines, report


if __name__ == "__main__":
    restaurants, cuisine_rows, quality = run_pipeline()
    print(f"Source: {quality['rows']:,} restaurants; {quality['columns']} columns")
    print(f"Output: {len(restaurants):,} restaurants; {len(cuisine_rows):,} cuisine rows")
    print(f"Duplicate IDs: {quality['duplicate_restaurant_ids']}")
    print(f"Missing cuisine values: {quality['missing_by_column']['cuisines']}")