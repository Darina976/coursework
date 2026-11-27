-- Справочник районов Амстердама
CREATE TABLE IF NOT EXISTS dim_location (
    location_id SERIAL PRIMARY KEY,
    neighbourhood VARCHAR(100) UNIQUE NOT NULL,
    neighbourhood_group VARCHAR(100),
    latitude_avg DECIMAL(9, 6),
    longitude_avg DECIMAL(9, 6),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Справочник владельцев (хостов)
CREATE TABLE IF NOT EXISTS dim_host (
    host_id BIGINT PRIMARY KEY,
    host_name VARCHAR(255),
    is_superhost BOOLEAN DEFAULT FALSE,
    listings_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Справочник типов недвижимости
CREATE TABLE IF NOT EXISTS dim_property (
    property_id SERIAL PRIMARY KEY,
    room_type VARCHAR(50) UNIQUE NOT NULL,
    property_type VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Справочник дат
CREATE TABLE IF NOT EXISTS dim_date (
    date_id DATE PRIMARY KEY,
    year INTEGER,
    month INTEGER,
    day INTEGER,
    day_of_week INTEGER,
    is_weekend BOOLEAN,
    scrape_date DATE
);

-- Факт-таблица: объекты размещения
CREATE TABLE IF NOT EXISTS fact_listings (
    listing_id BIGINT NOT NULL,
    scrape_date DATE NOT NULL,
    location_id INTEGER REFERENCES dim_location(location_id),
    host_id BIGINT REFERENCES dim_host(host_id),
    property_id INTEGER REFERENCES dim_property(property_id),
    name VARCHAR(255),
    price_eur DECIMAL(10, 2),
    minimum_nights INTEGER,
    number_of_reviews INTEGER,
    review_scores_rating DECIMAL(3, 2),
    availability_365 INTEGER,
    calculated_host_listings_count INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (listing_id, scrape_date)
);

-- Индексы
CREATE INDEX IF NOT EXISTS idx_fact_listings_scrape_date ON fact_listings(scrape_date);
CREATE INDEX IF NOT EXISTS idx_fact_listings_location ON fact_listings(location_id);
CREATE INDEX IF NOT EXISTS idx_fact_listings_host ON fact_listings(host_id);
CREATE INDEX IF NOT EXISTS idx_fact_listings_price ON fact_listings(price_eur);

-- Витрина для аналитики
CREATE OR REPLACE VIEW v_market_stats AS
SELECT
    dl.neighbourhood,
    dp.room_type,
    COUNT(fl.listing_id) AS total_listings,
    ROUND(AVG(fl.price_eur), 2) AS avg_price,
    ROUND(MIN(fl.price_eur), 2) AS min_price,
    ROUND(MAX(fl.price_eur), 2) AS max_price,
    ROUND(AVG(fl.review_scores_rating), 2) AS avg_rating,
    ROUND(AVG(fl.availability_365), 0) AS avg_availability
FROM fact_listings fl
JOIN dim_location dl ON fl.location_id = dl.location_id
JOIN dim_property dp ON fl.property_id = dp.property_id
WHERE fl.price_eur > 0
GROUP BY dl.neighbourhood, dp.room_type;
