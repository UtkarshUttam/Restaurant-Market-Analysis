-- Dataset-level checks after loading the processed CSVs.
SELECT COUNT(*) AS restaurant_rows,
       COUNT(DISTINCT restaurant_id) AS unique_restaurant_ids,
       COUNT(*) - COUNT(DISTINCT restaurant_id) AS duplicate_id_rows
FROM restaurants;

SELECT COUNT(*) AS exact_duplicate_id_rows
FROM (
    SELECT restaurant_id
    FROM restaurants
    GROUP BY restaurant_id
    HAVING COUNT(*) > 1
) AS duplicates;

SELECT
    COUNT(*) FILTER (WHERE cuisines IS NULL OR BTRIM(cuisines) = '') AS missing_cuisine,
    COUNT(*) FILTER (WHERE longitude IS NULL OR latitude IS NULL) AS missing_coordinates,
    COUNT(*) FILTER (WHERE aggregate_rating NOT BETWEEN 0 AND 5) AS invalid_rating,
    COUNT(*) FILTER (WHERE price_range NOT BETWEEN 1 AND 4) AS invalid_price_range,
    COUNT(*) FILTER (WHERE votes < 0) AS negative_votes,
    COUNT(*) FILTER (WHERE average_cost_for_two < 0) AS negative_cost
FROM restaurants;

SELECT flag_name, flag_value, COUNT(*) AS row_count
FROM restaurants
CROSS JOIN LATERAL (VALUES
    ('has_table_booking', has_table_booking),
    ('has_online_delivery', has_online_delivery),
    ('is_delivering_now', is_delivering_now),
    ('switch_to_order_menu', switch_to_order_menu)
) AS flags(flag_name, flag_value)
GROUP BY flag_name, flag_value
ORDER BY flag_name, flag_value;

-- Cost outlier screening is performed inside each currency; no rows are deleted.
WITH fences AS (
    SELECT currency,
           percentile_cont(0.25) WITHIN GROUP (ORDER BY average_cost_for_two) AS q1,
           percentile_cont(0.75) WITHIN GROUP (ORDER BY average_cost_for_two) AS q3
    FROM restaurants
    WHERE average_cost_for_two > 0
    GROUP BY currency
)
SELECT r.restaurant_id, r.city, r.currency, r.average_cost_for_two,
       f.q1, f.q3, f.q3 + 1.5 * (f.q3 - f.q1) AS upper_iqr_fence
FROM restaurants AS r
JOIN fences AS f USING (currency)
WHERE r.average_cost_for_two > f.q3 + 1.5 * (f.q3 - f.q1)
ORDER BY r.currency, r.average_cost_for_two DESC;