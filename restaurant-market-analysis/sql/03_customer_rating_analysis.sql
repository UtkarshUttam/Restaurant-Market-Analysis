SELECT AVG(aggregate_rating) FILTER (WHERE is_rated) AS average_rating,
       COUNT(*) FILTER (WHERE NOT is_rated) AS unrated_restaurants
FROM restaurants;

SELECT restaurant_id, restaurant_name, city, aggregate_rating, votes, cuisines
FROM restaurants
WHERE is_rated
ORDER BY aggregate_rating DESC, votes DESC
LIMIT 25;

SELECT restaurant_id, restaurant_name, city, aggregate_rating, votes
FROM restaurants
ORDER BY votes DESC
LIMIT 25;

SELECT price_range, COUNT(*) FILTER (WHERE is_rated) AS rated_restaurants,
       AVG(aggregate_rating) FILTER (WHERE is_rated) AS average_rating,
       percentile_cont(0.5) WITHIN GROUP (ORDER BY aggregate_rating)
           FILTER (WHERE is_rated) AS median_rating
FROM restaurants
GROUP BY price_range
ORDER BY price_range;

SELECT has_online_delivery, COUNT(*) FILTER (WHERE is_rated) AS rated_restaurants,
       AVG(aggregate_rating) FILTER (WHERE is_rated) AS average_rating,
       AVG(votes) AS average_votes
FROM restaurants
GROUP BY has_online_delivery;

SELECT has_table_booking, COUNT(*) FILTER (WHERE is_rated) AS rated_restaurants,
       AVG(aggregate_rating) FILTER (WHERE is_rated) AS average_rating,
       AVG(votes) AS average_votes
FROM restaurants
GROUP BY has_table_booking;

-- High-vote/low-rating uses explicit dataset quartiles, not a fixed claim threshold.
WITH cutoffs AS (
    SELECT percentile_cont(0.75) WITHIN GROUP (ORDER BY votes)
           FILTER (WHERE is_rated) AS high_vote_cutoff,
           percentile_cont(0.25) WITHIN GROUP (ORDER BY aggregate_rating)
               FILTER (WHERE is_rated) AS low_rating_cutoff
    FROM restaurants
)
SELECT r.restaurant_id, r.restaurant_name, r.city, r.aggregate_rating, r.votes
FROM restaurants AS r
CROSS JOIN cutoffs AS c
WHERE r.is_rated AND r.votes >= c.high_vote_cutoff
  AND r.aggregate_rating <= c.low_rating_cutoff
ORDER BY r.votes DESC;