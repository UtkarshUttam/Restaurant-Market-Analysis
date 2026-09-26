"""Build analysis tables, statistical results, opportunities, and figures."""

from pathlib import Path

from src.analysis import cuisine_opportunities, high_votes_low_ratings, statistical_report
from src.data_loader import CUISINE_DATA_PATH, PROCESSED_DATA_PATH, PROJECT_ROOT, load_processed_data
from src.visualization import create_figures


def main() -> None:
    """Run the complete analysis against pipeline outputs."""
    restaurants = load_processed_data(PROCESSED_DATA_PATH)
    cuisines = load_processed_data(CUISINE_DATA_PATH)
    report_dir = PROJECT_ROOT / "reports"
    report_dir.mkdir(exist_ok=True)

    correlations, tests = statistical_report(restaurants)
    correlations.to_csv(report_dir / "correlation_tests.csv", index=False)
    tests.to_csv(report_dir / "group_comparison_tests.csv", index=False)
    cuisine_opportunities(restaurants, cuisines).to_csv(
        report_dir / "cuisine_opportunities.csv", index=False
    )
    high_votes_low_ratings(restaurants).to_csv(
        report_dir / "high_votes_low_ratings.csv", index=False
    )
    figures = create_figures(restaurants, cuisines, report_dir / "figures")
    print(f"Saved {len(figures)} figures and analysis tables to {report_dir}")


if __name__ == "__main__":
    main()