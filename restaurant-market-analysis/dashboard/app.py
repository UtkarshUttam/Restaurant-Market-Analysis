"""Interactive restaurant market analysis dashboard."""

from pathlib import Path
import sys

import pandas as pd
import plotly.express as px
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.analysis import cuisine_opportunities, high_votes_low_ratings, market_summary, spatial_clusters  # noqa: E402
from src.data_cleaning import run_pipeline  # noqa: E402
from src.data_loader import CUISINE_DATA_PATH, PROCESSED_DATA_PATH, load_processed_data  # noqa: E402

COLORS = ["#176B5B", "#E07A45", "#38598B", "#E4B363", "#8F5D82"]
st.set_page_config(page_title="Restaurant Market Intelligence", page_icon="🍽", layout="wide")


@st.cache_data(show_spinner="Preparing restaurant data...")
def load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load processed files, creating them when a clone is run for the first time."""
    if not PROCESSED_DATA_PATH.exists() or not CUISINE_DATA_PATH.exists():
        run_pipeline()
    return load_processed_data(PROCESSED_DATA_PATH), load_processed_data(CUISINE_DATA_PATH)


def format_local_cost(data: pd.DataFrame) -> str:
    """Show a mean cost only when the current slice has one currency."""
    currency_count = data["currency"].nunique()
    if currency_count != 1:
        return "Multiple currencies" if currency_count else "N/A"
    currency = data["currency"].iloc[0]
    costs = data.loc[data["average_cost_for_two"].gt(0), "average_cost_for_two"]
    return f"{costs.mean():,.0f} {currency}" if not costs.empty else "N/A"


def build_sidebar(restaurants: pd.DataFrame, cuisines: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, str]:
    """Apply global sidebar filters and return restaurant and cuisine slices."""
    st.sidebar.header("Market filters")
    pages = ["Market overview", "Customer & ratings", "Pricing & cuisine",
             "Location analysis", "Digital services", "Market opportunities"]
    page = st.sidebar.radio("Dashboard section", pages)
    country_codes = sorted(restaurants["country_code"].dropna().unique().tolist())
    countries = st.sidebar.multiselect("Country code", country_codes)
    selected = restaurants.loc[restaurants["country_code"].isin(countries)] if countries else restaurants
    currencies = sorted(selected["currency"].dropna().unique().tolist())
    currency_filter = st.sidebar.multiselect("Currency", currencies)
    if currency_filter:
        selected = selected.loc[selected["currency"].isin(currency_filter)]
    city_options = sorted(selected["city"].dropna().unique().tolist())
    cities = st.sidebar.multiselect("City", city_options)
    if cities:
        selected = selected.loc[selected["city"].isin(cities)]

    cuisine_options = sorted(
        cuisines.loc[cuisines["restaurant_id"].isin(selected["restaurant_id"]), "cuisine"]
        .dropna().unique().tolist()
    )
    chosen_cuisines = st.sidebar.multiselect("Cuisine", cuisine_options)
    if chosen_cuisines:
        cuisine_ids = cuisines.loc[cuisines["cuisine"].isin(chosen_cuisines), "restaurant_id"].unique()
        selected = selected.loc[selected["restaurant_id"].isin(cuisine_ids)]

    selected_prices = st.sidebar.multiselect("Price range", [1, 2, 3, 4], default=[1, 2, 3, 4])
    selected = selected.loc[selected["price_range"].isin(selected_prices)]
    rating_range = st.sidebar.slider("Rating range (0 includes not rated)", 0.0, 4.9, (0.0, 4.9), 0.1)
    selected = selected.loc[selected["aggregate_rating"].between(*rating_range)]
    booking_filter = st.sidebar.selectbox("Table booking", ["All", "Yes", "No"])
    delivery_filter = st.sidebar.selectbox("Online delivery", ["All", "Yes", "No"])
    if booking_filter != "All":
        selected = selected.loc[selected["has_table_booking"].eq(booking_filter)]
    if delivery_filter != "All":
        selected = selected.loc[selected["has_online_delivery"].eq(delivery_filter)]

    selected_cuisine_rows = cuisines.loc[cuisines["restaurant_id"].isin(selected["restaurant_id"])]
    return selected, selected_cuisine_rows, page


def draw_overview(data: pd.DataFrame, cuisine_rows: pd.DataFrame) -> None:
    st.subheader("Market overview")
    if data.empty:
        st.info("No restaurants match the selected filters.")
        return
    summary = market_summary(data)
    metrics = st.columns(6)
    metrics[0].metric("Restaurants", f"{summary['restaurants']:,}")
    metrics[1].metric("Average rating", f"{summary['average_rating']:.2f}" if summary["rated_restaurants"] else "N/A")
    metrics[2].metric("Mean cost for two", format_local_cost(data))
    metrics[3].metric("Total votes", f"{summary['total_votes']:,}")
    metrics[4].metric("Cities", f"{summary['cities']:,}")
    metrics[5].metric("Cuisines", f"{summary['cuisines']:,}")
    if data["currency"].nunique() > 1:
        st.caption("The overall cost KPI requires a single-currency selection; detailed costs use separate currency panels. No conversion is applied.")

    left, right = st.columns(2)
    city_counts = data["city"].value_counts().head(12).rename_axis("City").reset_index(name="Restaurants")
    left.plotly_chart(px.bar(city_counts, x="Restaurants", y="City", orientation="h",
                             title="Restaurants by city", color_discrete_sequence=COLORS), width="stretch")
    rating_counts = data["rating_category"].value_counts().rename_axis("Rating category").reset_index(name="Restaurants")
    right.plotly_chart(px.bar(rating_counts, x="Rating category", y="Restaurants",
                              title="Rating distribution", color="Rating category", color_discrete_sequence=COLORS), width="stretch")
    left, right = st.columns(2)
    price = data["price_range"].value_counts().sort_index().rename_axis("Price range").reset_index(name="Restaurants")
    left.plotly_chart(px.bar(price, x="Price range", y="Restaurants", title="Price range distribution",
                             color_discrete_sequence=COLORS), width="stretch")
    top = cuisine_rows.groupby("cuisine")["restaurant_id"].nunique().nlargest(12).sort_values().reset_index(name="Restaurants")
    right.plotly_chart(px.bar(top, x="Restaurants", y="cuisine", orientation="h", title="Top cuisines",
                              color_discrete_sequence=COLORS), width="stretch")


def draw_ratings(data: pd.DataFrame, cuisine_rows: pd.DataFrame) -> None:
    st.subheader("Customer & rating analysis")
    if data.empty:
        st.info("No restaurants match the selected filters.")
        return
    rated = data.loc[data["is_rated"]]
    left, right = st.columns(2)
    left.plotly_chart(px.scatter(rated, x="votes", y="aggregate_rating", color="price_range",
                                 hover_name="restaurant_name", log_x=True, title="Votes vs rating",
                                 color_discrete_sequence=COLORS), width="stretch")
    by_price = rated.groupby("price_range", as_index=False)["aggregate_rating"].mean()
    right.plotly_chart(px.bar(by_price, x="price_range", y="aggregate_rating", title="Average rating by price range",
                              color_discrete_sequence=COLORS), width="stretch")
    cuisine_ratings = (cuisine_rows.loc[cuisine_rows["aggregate_rating"].gt(0)]
                       .groupby("cuisine").agg(average_rating=("aggregate_rating", "mean"),
                                                restaurants=("restaurant_id", "nunique"))
                       .query("restaurants >= 5").nlargest(15, "average_rating").reset_index())
    st.plotly_chart(px.bar(cuisine_ratings.sort_values("average_rating"), x="average_rating", y="cuisine",
                           orientation="h", title="Highest-rated cuisines (at least five restaurants)",
                           hover_data=["restaurants"], color_discrete_sequence=COLORS), width="stretch")
    st.markdown("**High-rated restaurants**")
    st.dataframe(rated.sort_values(["aggregate_rating", "votes"], ascending=False)[
        ["restaurant_name", "city", "cuisines", "aggregate_rating", "votes", "price_range"]
    ].head(15), width="stretch", hide_index=True)


def draw_pricing(data: pd.DataFrame, cuisine_rows: pd.DataFrame) -> None:
    st.subheader("Pricing & cuisine")
    if data.empty:
        st.info("No restaurants match the selected filters.")
        return
    cost = data.loc[data["average_cost_for_two"].gt(0)]
    city_cost = cost.groupby(["city", "currency"], as_index=False).agg(
        mean_cost=("average_cost_for_two", "mean"), restaurants=("restaurant_id", "nunique"))
    city_cost = city_cost.nlargest(20, "restaurants")
    city_cost_figure = px.bar(city_cost, x="city", y="mean_cost", facet_col="currency", facet_col_wrap=3,
                              title="Mean cost for two by city (separate currency panels)",
                              hover_data=["restaurants"], color_discrete_sequence=COLORS)
    city_cost_figure.update_yaxes(matches=None)
    st.plotly_chart(city_cost_figure, width="stretch")
    cuisine_cost = cuisine_rows.loc[cuisine_rows["average_cost_for_two"].gt(0)].groupby(
        ["cuisine", "currency"], as_index=False).agg(
            mean_cost=("average_cost_for_two", "mean"), restaurants=("restaurant_id", "nunique"))
    cuisine_cost = cuisine_cost.loc[cuisine_cost["restaurants"].ge(5)].nlargest(15, "restaurants")
    left, right = st.columns(2)
    cuisine_cost_figure = px.bar(cuisine_cost, x="cuisine", y="mean_cost", facet_col="currency",
                                 facet_col_wrap=2, title="Mean cost by cuisine (separate currency panels)",
                                 color_discrete_sequence=COLORS)
    cuisine_cost_figure.update_yaxes(matches=None)
    left.plotly_chart(cuisine_cost_figure, width="stretch")
    relative_cost = cost.copy()
    relative_cost["cost_percentile"] = relative_cost.groupby("currency")["average_cost_for_two"].rank(pct=True)
    relative_cost = relative_cost.loc[relative_cost["is_rated"]]
    right.plotly_chart(px.scatter(relative_cost, x="cost_percentile", y="aggregate_rating", color="price_range",
                                  hover_name="restaurant_name", title="Relative cost position vs rating",
                                  labels={"cost_percentile": "Cost percentile within currency"},
                                  color_discrete_sequence=COLORS), width="stretch")
    st.caption("Cost comparisons use local currency units or each restaurant's rank within its currency; raw costs are never pooled across currencies.")


def draw_location(data: pd.DataFrame) -> None:
    st.subheader("Location analysis")
    if data.empty:
        st.info("No restaurants match the selected filters.")
        return
    geo = data.dropna(subset=["longitude", "latitude"])
    if not geo.empty:
        st.plotly_chart(px.scatter_geo(geo, lon="longitude", lat="latitude", color="aggregate_rating",
                                       hover_name="restaurant_name", hover_data=["city", "locality", "currency"],
                                       title="Restaurant locations", color_continuous_scale="Viridis",
                                       opacity=0.65), width="stretch")
    else:
        st.info("No valid coordinates in this selection.")
    city = data.groupby(["city", "currency"], as_index=False).agg(
        restaurants=("restaurant_id", "nunique"),
        average_rating=("aggregate_rating", lambda values: values[data.loc[values.index, "is_rated"]].mean()),
        median_cost=("average_cost_for_two", "median"))
    left, right = st.columns(2)
    left.plotly_chart(px.bar(city.nlargest(15, "restaurants"), x="city", y="restaurants", color="currency",
                             title="Restaurant count by city", color_discrete_sequence=COLORS), width="stretch")
    right.plotly_chart(px.scatter(city, x="restaurants", y="average_rating", color="currency",
                                  size="restaurants", hover_name="city", title="City count vs average rating",
                                  color_discrete_sequence=COLORS), width="stretch")
    clusters = spatial_clusters(data)
    clustered = clusters.loc[clusters["cluster_label"].ge(0)]
    if clustered.empty:
        st.caption("No coordinate group meets the documented cluster threshold in this selection.")
    else:
        cluster_summary = (clustered.groupby(["country_code", "city", "cluster_label"], as_index=False)
                           .agg(restaurants=("restaurant_id", "nunique"),
                                latitude=("latitude", "mean"), longitude=("longitude", "mean")))
        st.caption("Dense location groups: DBSCAN within country-code/city, 500 m neighborhood, minimum 5 restaurants. Clusters describe recorded restaurant locations, not customer demand.")
        st.dataframe(cluster_summary.nlargest(15, "restaurants"), width="stretch", hide_index=True)


def draw_digital(data: pd.DataFrame) -> None:
    st.subheader("Digital services")
    if data.empty:
        st.info("No restaurants match the selected filters.")
        return
    fields = {"has_online_delivery": "Online delivery", "has_table_booking": "Table booking",
              "is_delivering_now": "Delivering now", "switch_to_order_menu": "Order menu"}
    adoption = pd.concat([
        data[column].value_counts().rename_axis("Availability").reset_index(name="Restaurants").assign(Service=label)
        for column, label in fields.items()
    ], ignore_index=True)
    totals = adoption.groupby("Service")["Restaurants"].transform("sum")
    adoption["Share (%)"] = adoption["Restaurants"] / totals * 100
    left, right = st.columns(2)
    left.plotly_chart(px.bar(adoption, x="Service", y="Share (%)", color="Availability", barmode="stack",
                             title="Digital-service availability", color_discrete_sequence=COLORS), width="stretch")
    rated = data.loc[data["is_rated"]].copy()
    rated["Online delivery"] = rated["has_online_delivery"]
    right.plotly_chart(px.box(rated, x="Online delivery", y="aggregate_rating",
                              title="Rating by online delivery availability", color="Online delivery",
                              color_discrete_sequence=COLORS), width="stretch")
    price_service = data.groupby(["price_range", "has_online_delivery"], as_index=False).agg(
        restaurants=("restaurant_id", "nunique"))
    st.plotly_chart(px.density_heatmap(price_service, x="price_range", y="has_online_delivery",
                                       z="restaurants", histfunc="sum", title="Online delivery by price range",
                                       color_continuous_scale="Tealgrn"), width="stretch")
    service_comparison = pd.concat([
        data.groupby(column, as_index=False).agg(
            restaurants=("restaurant_id", "nunique"), average_votes=("votes", "mean"),
            average_rating=("aggregate_rating", lambda values: values[data.loc[values.index, "is_rated"]].mean()),
        ).rename(columns={column: "Availability"}).assign(Service=label)
        for column, label in fields.items()
    ], ignore_index=True)
    st.plotly_chart(px.bar(service_comparison, x="Service", y="average_votes", color="Availability",
                           barmode="group", title="Mean votes by digital-service availability",
                           hover_data=["restaurants", "average_rating"], color_discrete_sequence=COLORS),
                  width="stretch")
    st.caption("Service and rating differences are observational associations, not evidence that a service causes higher ratings.")


def draw_opportunities(data: pd.DataFrame, cuisine_rows: pd.DataFrame) -> None:
    st.subheader("Market opportunity screening")
    if data.empty:
        st.info("No restaurants match the selected filters.")
        return
    st.info("This dataset has no sales, population, or time-series demand measures. Votes are review activity, not revenue or market demand; treat these as leads for further research, not predictions.")
    opportunities = cuisine_opportunities(data, cuisine_rows, minimum_cuisine_count=5)
    if opportunities.empty:
        st.write("No cuisine segment meets the minimum five rated restaurants in this selection.")
    else:
        st.markdown("**Cuisine screening: above-market rating with relatively low presence**")
        st.dataframe(opportunities[["currency", "cuisine", "restaurant_count", "average_rating",
                                   "market_rating", "rating_gap", "presence_percentile", "opportunity_score"]]
                     .head(20), width="stretch", hide_index=True)
        st.caption("Score = (cuisine mean rating - currency-group mean rating) x (1 - within-currency restaurant-count percentile). Ranking is descriptive and sample-sensitive.")
    city = data.groupby("city", as_index=False).agg(
        restaurants=("restaurant_id", "nunique"), rated_restaurants=("is_rated", "sum"),
        average_rating=("aggregate_rating", "mean"), votes_proxy=("votes", "sum"))
    st.markdown("**Location comparison: restaurant counts and review activity, not demand estimates**")
    st.dataframe(city.sort_values(["restaurants", "votes_proxy"], ascending=[True, False]).head(20),
                 width="stretch", hide_index=True)
    st.markdown("**High review activity with low relative rating**")
    st.dataframe(high_votes_low_ratings(data)[["restaurant_name", "city", "aggregate_rating", "votes"]].head(15),
                 width="stretch", hide_index=True)
    st.markdown("**High rating with relatively few votes**")
    low_visibility = data.loc[data["is_rated"] & data["aggregate_rating"].ge(4.0)
                              & data["votes"].le(data["votes"].quantile(0.25))]
    st.dataframe(low_visibility[["restaurant_name", "city", "cuisines", "aggregate_rating", "votes"]]
                 .sort_values("aggregate_rating", ascending=False).head(15),
                 width="stretch", hide_index=True)


def main() -> None:
    restaurants, cuisine_rows = load_data()
    st.title("Restaurant Market Intelligence Dashboard")
    st.caption("Restaurant coverage, ratings, pricing, cuisine mix, location, and digital-service indicators")
    data, cuisines, page = build_sidebar(restaurants, cuisine_rows)
    if page == "Market overview":
        draw_overview(data, cuisines)
    elif page == "Customer & ratings":
        draw_ratings(data, cuisines)
    elif page == "Pricing & cuisine":
        draw_pricing(data, cuisines)
    elif page == "Location analysis":
        draw_location(data)
    elif page == "Digital services":
        draw_digital(data)
    else:
        draw_opportunities(data, cuisines)


if __name__ == "__main__":
    main()