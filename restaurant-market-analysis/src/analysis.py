"""Business-facing summaries, statistical tests, and opportunity screening."""

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.cluster import DBSCAN


def market_summary(data: pd.DataFrame) -> dict[str, int | float]:
    """Summarize dataset scope while counting restaurants only once."""
    cuisines = {
        cuisine.strip()
        for values in data["cuisines"].dropna()
        for cuisine in values.split(",")
        if cuisine.strip()
    }
    rated = data.loc[data["is_rated"]]
    return {
        "restaurants": int(data["restaurant_id"].nunique()),
        "countries": int(data["country_code"].nunique()),
        "cities": int(data["city"].nunique()),
        "cuisines": len(cuisines),
        "total_votes": int(data["votes"].sum()),
        "average_rating": float(rated["aggregate_rating"].mean()) if len(rated) else float("nan"),
        "rated_restaurants": int(len(rated)),
    }


def compare_ratings(data: pd.DataFrame, flag: str) -> dict[str, float | int | str]:
    """Compare rated restaurants with/without a binary service using Welch's t-test."""
    eligible = data.loc[data["is_rated"] & data[flag].isin(["Yes", "No"])]
    yes = eligible.loc[eligible[flag].eq("Yes"), "aggregate_rating"]
    no = eligible.loc[eligible[flag].eq("No"), "aggregate_rating"]
    if len(yes) < 2 or len(no) < 2:
        return {"variable": flag, "test": "Welch independent t-test", "n_yes": len(yes),
                "n_no": len(no), "mean_yes": float(yes.mean()) if len(yes) else np.nan,
                "mean_no": float(no.mean()) if len(no) else np.nan,
                "statistic": np.nan, "p_value": np.nan}
    test = stats.ttest_ind(yes, no, equal_var=False, nan_policy="omit")
    return {"variable": flag, "test": "Welch independent t-test", "n_yes": len(yes),
            "n_no": len(no), "mean_yes": float(yes.mean()), "mean_no": float(no.mean()),
            "statistic": float(test.statistic), "p_value": float(test.pvalue)}


def statistical_report(data: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Run non-causal association tests and correlations on rated restaurants."""
    rated = data.loc[data["is_rated"]]
    correlations: list[dict[str, float | int | str]] = []
    pairs_to_test = [("votes", "aggregate_rating", rated)]
    rated_costs = rated.loc[rated["average_cost_for_two"].gt(0)]
    all_costs = data.loc[data["average_cost_for_two"].gt(0)]
    for _, group in rated_costs.groupby("currency"):
        pairs_to_test.append(("average_cost_for_two", "aggregate_rating", group))
    for _, group in all_costs.groupby("currency"):
        pairs_to_test.append(("average_cost_for_two", "votes", group))
    for left, right, group in pairs_to_test:
        pairs = group[[left, right]].dropna()
        result = stats.spearmanr(pairs[left], pairs[right]) if len(pairs) > 1 else None
        correlations.append({"currency": group["currency"].iloc[0] if left == "average_cost_for_two" and len(group) else "All currencies",
                             "variable_x": left, "variable_y": right, "test": "Spearman rank correlation",
                             "n": len(pairs), "statistic": float(result.statistic) if result else np.nan,
                             "p_value": float(result.pvalue) if result else np.nan})

    comparisons = [compare_ratings(data, column)
                   for column in ["has_online_delivery", "has_table_booking"]]
    price_samples = [group["aggregate_rating"].to_numpy()
                     for _, group in rated.groupby("price_range", observed=True)
                     if len(group) > 1]
    if len(price_samples) >= 2:
        test = stats.kruskal(*price_samples)
        comparisons.append({"variable": "price_range", "test": "Kruskal-Wallis test",
                            "n_yes": sum(map(len, price_samples)), "n_no": np.nan,
                            "mean_yes": np.nan, "mean_no": np.nan,
                            "statistic": float(test.statistic), "p_value": float(test.pvalue)})
    return pd.DataFrame(correlations), pd.DataFrame(comparisons)


def cuisine_opportunities(
    restaurants: pd.DataFrame,
    cuisine_rows: pd.DataFrame,
    minimum_cuisine_count: int = 5,
) -> pd.DataFrame:
    """Rank cuisines by rating-vs-presence gap within each currency.

    Score is the mean rating minus the mean rating of that currency group's
    restaurants, multiplied by one minus the cuisine's within-currency
    restaurant-count percentile. A minimum sample count limits unstable ranks.
    This is a screening heuristic, not a forecast or causal claim.
    """
    baseline = restaurants.loc[restaurants["is_rated"]].groupby(
        "currency", as_index=False
    )["aggregate_rating"].mean().rename(columns={"aggregate_rating": "market_rating"})
    summary = cuisine_rows.loc[cuisine_rows["aggregate_rating"].gt(0)].groupby(
        ["currency", "cuisine"], as_index=False
    ).agg(restaurant_count=("restaurant_id", "nunique"),
          average_rating=("aggregate_rating", "mean"), total_votes=("votes", "sum"))
    summary = summary.merge(baseline, on="currency", how="left")
    summary["rating_gap"] = summary["average_rating"] - summary["market_rating"]
    summary = summary.loc[summary["restaurant_count"].ge(minimum_cuisine_count)].copy()
    summary["presence_percentile"] = summary.groupby("currency")["restaurant_count"].rank(pct=True)
    summary["opportunity_score"] = summary["rating_gap"] * (1 - summary["presence_percentile"])
    return summary.sort_values("opportunity_score", ascending=False).reset_index(drop=True)


def high_votes_low_ratings(data: pd.DataFrame) -> pd.DataFrame:
    """Find high-vote/low-rated records using dataset-wide percentile thresholds."""
    rated = data.loc[data["is_rated"]].copy()
    if rated.empty:
        return rated
    return rated.loc[
        rated["votes"].ge(rated["votes"].quantile(0.75))
        & rated["aggregate_rating"].le(rated["aggregate_rating"].quantile(0.25))
    ].sort_values(["votes", "aggregate_rating"], ascending=[False, True])


def spatial_clusters(
    data: pd.DataFrame,
    radius_meters: float = 500,
    minimum_restaurants: int = 5,
) -> pd.DataFrame:
    """Label dense restaurant groups within each country-code/city pair.

    DBSCAN uses haversine distance over radians. Coordinates that were marked
    missing by cleaning are excluded; noise points retain label -1 and are not
    counted as a cluster. Parameters describe geographic proximity, not demand.
    """
    coordinate_rows = data.dropna(subset=["longitude", "latitude"]).copy()
    if coordinate_rows.empty:
        return coordinate_rows.assign(cluster_label=pd.Series(dtype="int64"),
                                      cluster_size=pd.Series(dtype="int64"))

    radius_earth_meters = 6_371_008.8
    epsilon = radius_meters / radius_earth_meters
    results: list[pd.DataFrame] = []
    for _, group in coordinate_rows.groupby(["country_code", "city"], dropna=False):
        coordinates = np.radians(group[["latitude", "longitude"]].to_numpy())
        labels = DBSCAN(eps=epsilon, min_samples=minimum_restaurants,
                        metric="haversine", algorithm="ball_tree").fit_predict(coordinates)
        clustered = group.copy()
        clustered["cluster_label"] = labels
        clustered["cluster_size"] = clustered.groupby("cluster_label")["restaurant_id"].transform("size")
        clustered.loc[clustered["cluster_label"].eq(-1), "cluster_size"] = 0
        results.append(clustered)
    return pd.concat(results, ignore_index=True)