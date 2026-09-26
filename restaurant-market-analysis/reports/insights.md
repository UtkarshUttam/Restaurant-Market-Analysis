# Snapshot Findings

**Scope:** 9,551 restaurant records from the supplied snapshot. One row represents one restaurant. Cuisine counts are distinct restaurants with a cuisine label and can exceed the total across categories because restaurants may list multiple cuisines.

## Observed Data

- All 9,551 restaurant IDs are unique; there are no exact duplicate rows. The file contains 21 fields, 15 country codes, 141 city labels, and 12 currency labels.
- 9 cuisine values are missing. There are 497 `(0, 0)` coordinate placeholders, retained as unknown coordinates rather than removed restaurants. There are 18 zero-cost records and 2,148 zero-rated records. All zero-rated records have `Rating text = Not rated`.
- 7,403 restaurants have a nonzero rating. Their mean aggregate rating is **3.44 / 5**. The mean is for the selected dataset and is not a global market estimate.
- The largest city counts are New Delhi (5,473), Gurgaon (1,118), Noida (1,080), and Faridabad (251). New Delhi alone accounts for 57.3% of the records. Coverage is highly concentrated.
- The most common cuisine labels are North Indian (3,960 distinct restaurants), Chinese (2,733), Fast Food (1,986), Mughlai (994), and Italian (764).
- With the dashboard's documented 500 m / five-point DBSCAN settings applied separately by city, 174 dense location clusters cover 7,455 of 9,054 restaurants with valid coordinates. This is a geographic concentration measure, not a measure of foot traffic or demand.
- Online delivery is marked Yes for 2,451 of 9,551 restaurants (25.66%); table booking for 1,158 (12.12%); currently delivering for 34 (0.36%). `Switch to order menu` is No for all records.
- Mean rating by price range among rated restaurants is 3.239 (range 1), 3.377 (2), 3.777 (3), and 3.891 (4).
- The largest recorded cost is 800,000 Indonesian Rupiah for Skye in Jakarta. The per-currency IQR review also flags 813 positive-cost Indian Rupee observations above their group upper fence. These observations are retained and warrant source-level review.

## Statistical Results

All tests below are observational. The outputs are in `correlation_tests.csv` and `group_comparison_tests.csv`.

- **Votes and rating:** Spearman rho = 0.682, n = 7,403, p < 0.001. In this snapshot, higher vote counts tend to rank with higher ratings. This does not mean votes cause ratings or represent sales.
- **Online delivery and rating:** rated restaurants with delivery average 3.381 (n = 2,355), versus 3.467 without delivery (n = 5,048); Welch t = -6.329, p < 0.001.
- **Table booking and rating:** rated restaurants with booking average 3.588 (n = 1,111), versus 3.414 without booking (n = 6,292); Welch t = 9.919, p < 0.001.
- **Price range and rating:** Kruskal-Wallis H = 1,326.067 across four price bands, n = 7,403, p < 0.001. The band-wise mean pattern is not a causal effect of price.
- **Cost associations:** Spearman tests are performed separately within each currency; effect estimates vary across currencies and sample sizes. Small currency groups make these tests exploratory. No exchange-rate normalization is available.

P-values are not adjusted for multiple testing across currency groups. Statistical significance does not establish practical significance; country, city, sample selection, and review behaviors may confound group differences.

## Analytical Interpretation

- The snapshot is primarily useful for examining the India-heavy coverage represented here; a global claim would overstate the sample.
- Higher price bands have higher mean ratings in this data, and booking availability is associated with a higher mean rating. Neither result shows that charging more or adding booking improves ratings.
- The delivery group has a slightly lower observed mean rating. This is not evidence that delivery harms ratings; market, restaurant mix, and selection effects could explain the difference.
- City counts and votes describe platform coverage and review activity only. The data has no population, sales, transactions, or capacity measures to estimate unmet demand or competition intensity.

## Follow-up Recommendations

1. Review the flagged high-cost records against the original source and local currency context before using them in pricing decisions; do not delete them solely for exceeding an IQR fence.
2. Investigate above-market-rated, relatively low-presence cuisine segments as hypotheses for customer research. The current scoring heuristic is not a launch recommendation.
3. Compare digital-service groups within the same country, city, and price bands before making operational decisions.
4. Obtain representative market coverage, population, transaction/sales, rent, and verified exchange-rate data before estimating opportunity, affordability across countries, or expected return.
5. Treat high-vote/low-rating and high-rating/low-vote restaurants as candidates for operational review or visibility research, not proof of dissatisfaction or hidden demand.

## Reproducibility

Rebuild the report outputs with `python -m src.data_cleaning` followed by `python -m src.run_analysis`. The opportunity formula and thresholds are documented in `README.md`, `src/analysis.py`, and `sql/06_business_opportunities.sql`.
