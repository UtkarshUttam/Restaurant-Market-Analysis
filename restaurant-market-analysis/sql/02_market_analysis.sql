SELECT COUNT(*) AS restaurants,
       COUNT(DISTINCT country_code) AS country_codes,
       COUNT(DISTINCT city) AS cities,
       SUM(votes) AS total_votes
FROM restaurants;

SELECT country_code, COUNT(*) AS restaurants
FROM restaurants
GROUP BY country_code
ORDER BY restaurants DESC;

SELECT city, COUNT(*) AS restaurants,
       COUNT(*) FILTER (WHERE is_rated) AS rated_restaurants
FROM restaurants
GROUP BY city
ORDER BY restaurants DESC
LIMIT 25;

SELECT price_range, COUNT(*) AS restaurants,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS share_percent
FROM restaurants
GROUP BY price_range
ORDER BY price_range;

SELECT rating_category, COUNT(*) AS restaurants
FROM restaurants
GROUP BY rating_category
ORDER BY CASE rating_category
    WHEN 'Not rated' THEN 0 WHEN 'Low' THEN 1 WHEN 'Fair' THEN 2
    WHEN 'Good' THEN 3 WHEN 'Very good' THEN 4 ELSE 5 END;

WITH city_summary AS (
    SELECT country_code, city, COUNT(*) AS restaurants,
           AVG(aggregate_rating) FILTER (WHERE is_rated) AS average_rating,
           SUM(votes) AS total_votes
    FROM restaurants
    GROUP BY country_code, city
)
SELECT *, DENSE_RANK() OVER (PARTITION BY country_code ORDER BY restaurants DESC) AS city_rank
FROM city_summary
ORDER BY restaurants DESC;