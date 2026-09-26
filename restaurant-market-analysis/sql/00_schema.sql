-- Load data/processed/restaurants_clean.csv and restaurant_cuisines.csv here.
CREATE TABLE IF NOT EXISTS restaurants (
    restaurant_id BIGINT PRIMARY KEY,
    restaurant_name TEXT,
    country_code INTEGER,
    city TEXT,
    address TEXT,
    locality TEXT,
    locality_verbose TEXT,
    longitude DOUBLE PRECISION,
    latitude DOUBLE PRECISION,
    cuisines TEXT,
    average_cost_for_two NUMERIC,
    currency TEXT,
    has_table_booking TEXT,
    has_online_delivery TEXT,
    is_delivering_now TEXT,
    switch_to_order_menu TEXT,
    price_range SMALLINT,
    aggregate_rating NUMERIC,
    rating_color TEXT,
    rating_text TEXT,
    votes INTEGER,
    cuisine_count SMALLINT,
    is_rated BOOLEAN,
    is_high_rated BOOLEAN,
    is_low_rated BOOLEAN,
    is_affordable BOOLEAN,
    is_expensive BOOLEAN,
    has_digital_service BOOLEAN,
    has_booking_or_delivery BOOLEAN,
    rating_category TEXT,
    vote_category TEXT,
    cost_category TEXT
);

CREATE TABLE IF NOT EXISTS restaurant_cuisines (
    restaurant_id BIGINT NOT NULL REFERENCES restaurants (restaurant_id),
    country_code INTEGER,
    city TEXT,
    locality TEXT,
    currency TEXT,
    average_cost_for_two NUMERIC,
    price_range SMALLINT,
    aggregate_rating NUMERIC,
    votes INTEGER,
    has_table_booking TEXT,
    has_online_delivery TEXT,
    cuisine TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_restaurants_city ON restaurants (city);
CREATE INDEX IF NOT EXISTS idx_restaurants_country ON restaurants (country_code);
CREATE INDEX IF NOT EXISTS idx_restaurant_cuisines_cuisine ON restaurant_cuisines (cuisine);