"""Restaurant-level and cuisine-level analytical feature construction."""

import pandas as pd


def add_features(data: pd.DataFrame) -> pd.DataFrame:
    """Add interpretable indicators without changing source observations."""
    result = data.copy()
    result["cuisine_count"] = result["cuisines"].map(
        lambda value: len([item for item in str(value).split(",") if item.strip()])
        if pd.notna(value)
        else 0
    )
    result["is_rated"] = result["aggregate_rating"].gt(0)
    result["is_high_rated"] = result["aggregate_rating"].ge(4.0)
    result["is_low_rated"] = result["aggregate_rating"].between(0.1, 2.9)
    result["is_affordable"] = result["price_range"].eq(1)
    result["is_expensive"] = result["price_range"].eq(4)
    result["has_digital_service"] = (
        result[["has_online_delivery", "is_delivering_now", "switch_to_order_menu"]]
        .eq("Yes")
        .any(axis=1)
    )
    result["has_booking_or_delivery"] = (
        result[["has_table_booking", "has_online_delivery"]].eq("Yes").any(axis=1)
    )
    result["rating_category"] = pd.cut(
        result["aggregate_rating"],
        bins=[-0.01, 0, 2.9, 3.4, 3.9, 4.4, 5.0],
        labels=["Not rated", "Low", "Fair", "Good", "Very good", "Excellent"],
    ).astype("string")
    result["vote_category"] = pd.cut(
        result["votes"],
        bins=[-1, 0, 10, 100, 500, float("inf")],
        labels=["No votes", "1-10", "11-100", "101-500", "501+"],
    ).astype("string")
    result["cost_category"] = "Unknown"
    positive_cost = result["average_cost_for_two"].gt(0)
    result.loc[positive_cost, "cost_category"] = (
        result.loc[positive_cost].groupby("currency")["average_cost_for_two"]
        .transform(
            lambda values: pd.qcut(
                values.rank(method="first"), 4, labels=False, duplicates="drop"
            ).astype("Int64").astype("string")
        )
        .map({"0": "Low within currency", "1": "Lower-middle within currency",
              "2": "Upper-middle within currency", "3": "High within currency"})
        .fillna("Insufficient currency group")
    )
    return result


def explode_cuisines(data: pd.DataFrame) -> pd.DataFrame:
    """Return one row per restaurant-cuisine pair; missing cuisine stays absent."""
    columns = [
        "restaurant_id", "country_code", "city", "locality", "currency",
        "average_cost_for_two", "price_range", "aggregate_rating", "votes",
        "has_table_booking", "has_online_delivery", "cuisines",
    ]
    result = data[columns].copy()
    result["cuisine"] = result["cuisines"].astype("string").str.split(",")
    result = result.explode("cuisine")
    result["cuisine"] = result["cuisine"].astype("string").str.strip()
    result = result.drop(columns="cuisines")
    return result.loc[result["cuisine"].notna() & result["cuisine"].ne("")].reset_index(drop=True)