-- Transparent cuisine screening score:
-- (cuisine mean rating - currency-group market mean rating)
-- * (1 - within-currency restaurant-count percentile).
-- Require >= 5 rated restaurants; this is a heuristic for investigation,
-- not a demand estimate, forecast, or recommendation guarantee.
WITH market_baseline AS (
    SELECT currency, AVG(aggregate_rating) AS market_rating
    FROM restaurants
    WHERE is_rated
    GROUP BY currency
), cuisine_metrics AS (
    SELECT c.currency, c.cuisine,
           COUNT(DISTINCT c.restaurant_id) FILTER (WHERE c.aggregate_rating > 0) AS restaurant_count,
           AVG(c.aggregate_rating) FILTER (WHERE c.aggregate_rating > 0) AS average_rating,
           SUM(c.votes) AS total_votes
    FROM restaurant_cuisines AS c
    GROUP BY c.currency, c.cuisine
    HAVING COUNT(DISTINCT c.restaurant_id) FILTER (WHERE c.aggregate_rating > 0) >= 5
), scored AS (
    SELECT m.*, b.market_rating,
           m.average_rating - b.market_rating AS rating_gap,
           percent_rank() OVER (PARTITION BY m.currency ORDER BY m.restaurant_count) AS presence_percentile
    FROM cuisine_metrics AS m
    JOIN market_baseline AS b USING (currency)
)
SELECT *, rating_gap * (1 - presence_percentile) AS opportunity_score
FROM scored
ORDER BY opportunity_score DESC;

-- Lower restaurant count is descriptive only; no external demand denominator exists.
SELECT country_code, city, COUNT(*) AS restaurant_count,
       COUNT(*) FILTER (WHERE is_rated) AS rated_restaurants,
       AVG(aggregate_rating) FILTER (WHERE is_rated) AS average_rating,
       SUM(votes) AS votes_proxy_not_revenue
FROM restaurants
GROUP BY country_code, city
HAVING COUNT(*) >= 5
ORDER BY restaurant_count ASC, votes_proxy_not_revenue DESC;

-- High visibility/vote counts with low relative ratings are diagnostic candidates.
WITH thresholds AS (
    SELECT percentile_cont(0.75) WITHIN GROUP (ORDER BY votes)
               FILTER (WHERE is_rated) AS votes_q75,
           percentile_cont(0.25) WITHIN GROUP (ORDER BY aggregate_rating)
               FILTER (WHERE is_rated) AS rating_q25
    FROM restaurants
)
SELECT r.restaurant_id, r.restaurant_name, r.city, r.aggregate_rating, r.votes
FROM restaurants AS r CROSS JOIN thresholds AS t
WHERE r.is_rated AND r.votes >= t.votes_q75 AND r.aggregate_rating <= t.rating_q25
ORDER BY r.votes DESC;