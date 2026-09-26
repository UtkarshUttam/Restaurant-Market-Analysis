"""Tests for the restaurant data pipeline and core quality contracts."""

import unittest

import pandas as pd

from src.analysis import spatial_clusters
from src.data_cleaning import clean_data, profile_data
from src.data_loader import load_raw_data
from src.feature_engineering import explode_cuisines


class DataPipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.raw = load_raw_data()
        cls.cleaned = clean_data(cls.raw)

    def test_dataset_loads_and_has_required_fields(self) -> None:
        self.assertEqual(len(self.raw), 9551)
        self.assertIn("Restaurant ID", self.raw.columns)
        quality = profile_data(self.raw)
        self.assertEqual(quality["exact_duplicate_rows"], 0)
        self.assertEqual(quality["duplicate_restaurant_ids"], 0)
        self.assertEqual(quality["missing_by_column"]["cuisines"], 9)
        self.assertIn("cost_outliers_by_currency", quality)
        self.assertIn("votes", quality["numeric_outlier_summary"])

    def test_restaurant_ids_are_unique_and_preserved(self) -> None:
        self.assertEqual(self.cleaned["restaurant_id"].nunique(), len(self.raw))
        self.assertEqual(len(self.cleaned), len(self.raw))

    def test_rating_and_price_ranges_are_valid(self) -> None:
        self.assertTrue(self.cleaned["aggregate_rating"].between(0, 5).all())
        self.assertTrue(self.cleaned["price_range"].isin([1, 2, 3, 4]).all())

    def test_coordinates_and_service_values_are_valid(self) -> None:
        self.assertTrue(self.cleaned["longitude"].dropna().between(-180, 180).all())
        self.assertTrue(self.cleaned["latitude"].dropna().between(-90, 90).all())
        for column in ["has_table_booking", "has_online_delivery", "is_delivering_now", "switch_to_order_menu"]:
            self.assertTrue(self.cleaned[column].dropna().isin(["Yes", "No"]).all())

    def test_invalid_numeric_values_become_missing_not_fabricated(self) -> None:
        sample = self.raw.head(1).copy()
        sample.loc[:, "Aggregate rating"] = 5.5
        sample.loc[:, "Price range"] = 0
        sample.loc[:, "Votes"] = -1
        sample.loc[:, "Average Cost for two"] = -1
        sample.loc[:, "Latitude"] = 91
        cleaned = clean_data(sample).iloc[0]
        for column in ["aggregate_rating", "price_range", "votes", "average_cost_for_two", "latitude"]:
            self.assertTrue(pd.isna(cleaned[column]), column)

    def test_expected_features_and_cuisine_explosion(self) -> None:
        for column in ["cuisine_count", "is_rated", "has_digital_service", "rating_category", "cost_category"]:
            self.assertIn(column, self.cleaned.columns)
        cuisines = explode_cuisines(self.cleaned)
        self.assertEqual(cuisines["restaurant_id"].nunique(), self.cleaned["cuisine_count"].gt(0).sum())
        self.assertGreater(len(cuisines), len(self.cleaned))

    def test_spatial_clusters_exclude_noise_and_use_local_points(self) -> None:
        points = pd.DataFrame({
            "restaurant_id": [1, 2, 3, 4, 5, 6],
            "country_code": [1] * 6,
            "city": ["A"] * 6,
            "latitude": [0, 0.0001, -0.0001, 0.0002, -0.0002, 0.1],
            "longitude": [0, 0.0001, -0.0001, -0.0002, 0.0002, 0.1],
        })
        clustered = spatial_clusters(points)
        dense = clustered.loc[clustered["cluster_label"].ge(0)]
        noise = clustered.loc[clustered["cluster_label"].eq(-1)]
        self.assertEqual(len(dense), 5)
        self.assertEqual(dense["cluster_size"].nunique(), 1)
        self.assertEqual(dense["cluster_size"].iloc[0], 5)
        self.assertTrue(noise["cluster_size"].eq(0).all())


if __name__ == "__main__":
    unittest.main()