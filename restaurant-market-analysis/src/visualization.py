"""Consistent, currency-aware static plots for the analysis report."""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

PALETTE = ["#176B5B", "#E07A45", "#38598B", "#E4B363", "#8F5D82"]


def _save(figure: plt.Figure, destination: Path) -> None:
    figure.tight_layout()
    figure.savefig(destination, dpi=160, bbox_inches="tight")
    plt.close(figure)


def create_figures(
    restaurants: pd.DataFrame,
    cuisine_rows: pd.DataFrame,
    output_dir: str | Path,
) -> list[Path]:
    """Generate the requested core EDA charts as clean PNG report assets."""
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    sns.set_theme(style="whitegrid", palette=PALETTE, font_scale=0.9,
                  rc={"font.family": "DejaVu Sans"})
    figures: list[Path] = []

    def finish(fig: plt.Figure, name: str) -> None:
        path = destination / name
        _save(fig, path)
        figures.append(path)

    top_city = restaurants["city"].value_counts().head(15).sort_values()
    fig, ax = plt.subplots(figsize=(10, 6))
    top_city.plot.barh(ax=ax, color=PALETTE[0])
    ax.set(title="Restaurants by city", xlabel="Restaurant count", ylabel="City")
    finish(fig, "restaurants_by_city.png")

    top_country = restaurants["country_code"].value_counts().sort_values()
    fig, ax = plt.subplots(figsize=(9, 5))
    top_country.plot.barh(ax=ax, color=PALETTE[2])
    ax.set(title="Restaurants by country code", xlabel="Restaurant count", ylabel="Country code")
    finish(fig, "restaurants_by_country.png")

    fig, ax = plt.subplots(figsize=(7, 4))
    sns.countplot(data=restaurants, x="price_range", order=[1, 2, 3, 4], ax=ax, color=PALETTE[0])
    ax.set(title="Price range distribution", xlabel="Price range (1 = lowest, 4 = highest)", ylabel="Restaurants")
    finish(fig, "price_range_distribution.png")

    rating_order = ["Not rated", "Low", "Fair", "Good", "Very good", "Excellent"]
    fig, ax = plt.subplots(figsize=(8, 4))
    sns.countplot(data=restaurants, x="rating_category", order=rating_order, ax=ax, color=PALETTE[1])
    ax.tick_params(axis="x", rotation=20)
    ax.set(title="Restaurant rating distribution", xlabel="Rating category", ylabel="Restaurants")
    finish(fig, "rating_distribution.png")

    top_cuisines = cuisine_rows.groupby("cuisine")["restaurant_id"].nunique().nlargest(15).sort_values()
    fig, ax = plt.subplots(figsize=(10, 6))
    top_cuisines.plot.barh(ax=ax, color=PALETTE[0])
    ax.set(title="Most common cuisines", xlabel="Restaurants offering cuisine", ylabel="Cuisine")
    finish(fig, "top_cuisines.png")

    cuisine_rating = (cuisine_rows.loc[cuisine_rows["aggregate_rating"].gt(0)]
                      .groupby("cuisine").agg(average_rating=("aggregate_rating", "mean"),
                                                restaurants=("restaurant_id", "nunique")))
    cuisine_rating = cuisine_rating.loc[cuisine_rating["restaurants"].ge(50)].nlargest(15, "average_rating")
    fig, ax = plt.subplots(figsize=(10, 6))
    cuisine_rating["average_rating"].sort_values().plot.barh(ax=ax, color=PALETTE[2])
    ax.set(title="Highest-rated cuisines (at least 50 restaurants)", xlabel="Mean rating (rated restaurants)", ylabel="Cuisine")
    finish(fig, "average_rating_by_cuisine.png")

    city_rating = (restaurants.loc[restaurants["is_rated"]].groupby("city")
                   .agg(average_rating=("aggregate_rating", "mean"), restaurants=("restaurant_id", "nunique")))
    city_rating = city_rating.loc[city_rating["restaurants"].ge(30)].nlargest(15, "average_rating")
    fig, ax = plt.subplots(figsize=(10, 6))
    city_rating["average_rating"].sort_values().plot.barh(ax=ax, color=PALETTE[0])
    ax.set(title="Average rating by city (at least 30 restaurants)", xlabel="Mean rating", ylabel="City")
    finish(fig, "average_rating_by_city.png")

    city_cost = (restaurants.loc[restaurants["average_cost_for_two"].gt(0)]
                 .groupby(["city", "currency"], as_index=False)
                 .agg(mean_cost=("average_cost_for_two", "mean"), restaurants=("restaurant_id", "nunique")))
    city_cost = city_cost.loc[city_cost["restaurants"].ge(10)]
    city_cost = city_cost.loc[city_cost["currency"].isin(city_cost.groupby("currency")["restaurants"].sum().nlargest(6).index)]
    grid = sns.catplot(data=city_cost, x="city", y="mean_cost", col="currency", col_wrap=3,
                       kind="bar", sharey=False, color=PALETTE[0], height=3.5, aspect=1.35)
    grid.set_axis_labels("City", "Mean cost in local currency")
    grid.set_titles("{col_name}")
    for ax in grid.axes.flat:
        ax.tick_params(axis="x", rotation=35)
    grid.figure.suptitle("Mean cost for two by city (separate currency panels)", y=1.03)
    path = destination / "cost_by_city_currency.png"
    grid.figure.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(grid.figure)
    figures.append(path)

    normalized = restaurants.loc[restaurants["average_cost_for_two"].gt(0)].copy()
    normalized["cost_percentile"] = normalized.groupby("currency")["average_cost_for_two"].rank(pct=True)
    normalized = normalized.loc[normalized["is_rated"]]
    fig, ax = plt.subplots(figsize=(8, 5))
    sns.scatterplot(data=normalized, x="cost_percentile", y="aggregate_rating", hue="price_range",
                    alpha=0.45, s=22, palette=PALETTE[:4], ax=ax, legend="brief")
    ax.set(title="Relative cost position vs rating", xlabel="Cost percentile within currency", ylabel="Aggregate rating")
    finish(fig, "relative_cost_vs_rating.png")

    fig, ax = plt.subplots(figsize=(8, 5))
    sns.scatterplot(data=restaurants.loc[restaurants["is_rated"]], x="votes", y="aggregate_rating",
                    alpha=0.35, s=20, color=PALETTE[2], ax=ax)
    ax.set_xscale("symlog", linthresh=1)
    ax.set(title="Votes vs rating", xlabel="Votes (symmetric log scale)", ylabel="Aggregate rating")
    finish(fig, "votes_vs_rating.png")

    for field, title, filename in [
        ("has_online_delivery", "Online delivery adoption", "online_delivery_adoption.png"),
        ("has_table_booking", "Table booking adoption", "table_booking_adoption.png"),
    ]:
        counts = restaurants[field].value_counts().reindex(["Yes", "No"], fill_value=0)
        fig, ax = plt.subplots(figsize=(6, 4))
        counts.plot.bar(ax=ax, color=[PALETTE[0], PALETTE[1]])
        ax.set(title=title, xlabel="Availability", ylabel="Restaurants")
        finish(fig, filename)

    rated = restaurants.loc[restaurants["is_rated"]].copy()
    rated["digital_services"] = rated["has_online_delivery"].map({"Yes": "Online delivery", "No": "No online delivery"})
    fig, ax = plt.subplots(figsize=(7, 5))
    sns.boxplot(data=rated, x="digital_services", y="aggregate_rating", ax=ax, color=PALETTE[3])
    ax.set(title="Rating by online delivery availability", xlabel="Service status", ylabel="Aggregate rating")
    finish(fig, "rating_by_digital_services.png")

    city_list = restaurants["city"].value_counts().head(12).index
    cuisine_list = cuisine_rows["cuisine"].value_counts().head(12).index
    heat = (cuisine_rows.loc[cuisine_rows["city"].isin(city_list) & cuisine_rows["cuisine"].isin(cuisine_list)]
            .pivot_table(index="city", columns="cuisine", values="restaurant_id", aggfunc="nunique", fill_value=0))
    fig, ax = plt.subplots(figsize=(12, 8))
    sns.heatmap(heat, cmap="YlGnBu", linewidths=0.2, ax=ax)
    ax.set(title="Restaurant-cuisine presence across leading cities", xlabel="Cuisine", ylabel="City")
    finish(fig, "cuisine_by_city_heatmap.png")

    geo = restaurants.dropna(subset=["longitude", "latitude"])
    fig, ax = plt.subplots(figsize=(11, 6))
    points = ax.scatter(geo["longitude"], geo["latitude"], c=geo["aggregate_rating"],
                        cmap="viridis", s=8, alpha=0.55, linewidths=0)
    fig.colorbar(points, ax=ax, label="Aggregate rating (0 means not rated)")
    ax.set(title="Geographic distribution of restaurants", xlabel="Longitude", ylabel="Latitude")
    finish(fig, "geographic_distribution.png")
    return figures