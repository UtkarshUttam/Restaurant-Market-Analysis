SELECT cuisine, COUNT(DISTINCT restaurant_id) AS restaurant_count,
       SUM(votes) AS associated_votes
FROM restaurant_cuisines
GROUP BY cuisine
ORDER BY restaurant_count DESC
LIMIT 30;

SELECT cuisine, COUNT(DISTINCT restaurant_id) AS restaurants,
       AVG(aggregate_rating) FILTER (WHERE aggregate_rating > 0) AS average_rating,
       SUM(votes) AS associated_votes
FROM restaurant_cuisines
GROUP BY cuisine
HAVING COUNT(DISTINCT restaurant_id) >= 30
ORDER BY average_rating DESC;

WITH cuisine_city AS (
    SELECT city, cuisine, COUNT(DISTINCT restaurant_id) AS restaurants,
           SUM(votes) AS associated_votes,
           RANK() OVER (PARTITION BY city ORDER BY COUNT(DISTINCT restaurant_id) DESC) AS cuisine_rank
    FROM restaurant_cuisines
    GROUP BY city, cuisine
)
SELECT city, cuisine, restaurants, associated_votes
FROM cuisine_city
WHERE cuisine_rank <= 3
ORDER BY city, cuisine_rank;

-- Joining exploded cuisine rows is safe for cuisine questions only.
-- Count DISTINCT restaurant_id to avoid multi-cuisine inflation.
SELECT c.cuisine, r.currency, COUNT(DISTINCT r.restaurant_id) AS restaurant_count,
       AVG(r.aggregate_rating) FILTER (WHERE r.is_rated) AS average_rating,
       AVG(r.average_cost_for_two) FILTER (WHERE r.average_cost_for_two > 0) AS mean_local_cost
FROM restaurant_cuisines AS c
JOIN restaurants AS r USING (restaurant_id)
GROUP BY c.cuisine, r.currency
HAVING COUNT(DISTINCT r.restaurant_id) >= 5
ORDER BY r.currency, restaurant_count DESC;