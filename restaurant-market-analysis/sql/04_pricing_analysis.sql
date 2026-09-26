-- Never aggregate raw costs across currencies.
SELECT city, currency, COUNT(*) AS restaurants,
       AVG(average_cost_for_two) AS mean_cost_for_two,
       percentile_cont(0.5) WITHIN GROUP (ORDER BY average_cost_for_two) AS median_cost_for_two
FROM restaurants
WHERE average_cost_for_two > 0
GROUP BY city, currency
HAVING COUNT(*) >= 5
ORDER BY restaurants DESC;

SELECT currency, price_range, COUNT(*) AS restaurants,
       AVG(average_cost_for_two) AS mean_cost_for_two,
       AVG(aggregate_rating) FILTER (WHERE is_rated) AS average_rating
FROM restaurants
GROUP BY currency, price_range
ORDER BY currency, price_range;

SELECT restaurant_id, restaurant_name, city, currency, average_cost_for_two,
       price_range, aggregate_rating, votes
FROM restaurants
WHERE is_rated AND price_range = 1 AND aggregate_rating >= 4.0
ORDER BY aggregate_rating DESC, votes DESC;

SELECT restaurant_id, restaurant_name, city, currency, average_cost_for_two,
       price_range, aggregate_rating, votes
FROM restaurants
WHERE is_rated AND price_range = 4 AND aggregate_rating >= 4.0
ORDER BY aggregate_rating DESC, votes DESC;

-- Within-currency Spearman-style exploration should be calculated in Python;
-- this query supplies the unconverted observations for that analysis.
SELECT currency, average_cost_for_two, aggregate_rating, votes
FROM restaurants
WHERE average_cost_for_two > 0 AND is_rated;