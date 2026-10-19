-- ============================================================
-- INCREMENTAL DIMENSION LOAD
-- Does not truncate existing dimension tables.
-- ============================================================

-- CUSTOMER DIMENSION

INSERT INTO warehouse.dim_customer AS target (
    customer_id,
    first_name,
    last_name,
    email,
    gender,
    date_of_birth,
    signup_date,
    city,
    state,
    country
)
SELECT
    customer_id,
    first_name,
    last_name,
    email,
    gender,
    date_of_birth,
    signup_date,
    city,
    state,
    country
FROM clean.customers

ON CONFLICT (customer_id)
DO UPDATE SET
    first_name = EXCLUDED.first_name,
    last_name = EXCLUDED.last_name,
    email = EXCLUDED.email,
    gender = EXCLUDED.gender,
    date_of_birth = EXCLUDED.date_of_birth,
    signup_date = EXCLUDED.signup_date,
    city = EXCLUDED.city,
    state = EXCLUDED.state,
    country = EXCLUDED.country

WHERE ROW(
    target.first_name, target.last_name, target.email,
    target.gender, target.date_of_birth, target.signup_date,
    target.city, target.state, target.country
) IS DISTINCT FROM ROW(
    EXCLUDED.first_name, EXCLUDED.last_name, EXCLUDED.email,
    EXCLUDED.gender, EXCLUDED.date_of_birth, EXCLUDED.signup_date,
    EXCLUDED.city, EXCLUDED.state, EXCLUDED.country
);


-- PRODUCT DIMENSION

INSERT INTO warehouse.dim_product AS target (
    product_id,
    product_name,
    category,
    subcategory,
    brand,
    price,
    cost
)
SELECT
    product_id,
    product_name,
    category,
    subcategory,
    brand,
    price,
    cost
FROM clean.products

ON CONFLICT (product_id)
DO UPDATE SET
    product_name = EXCLUDED.product_name,
    category = EXCLUDED.category,
    subcategory = EXCLUDED.subcategory,
    brand = EXCLUDED.brand,
    price = EXCLUDED.price,
    cost = EXCLUDED.cost

WHERE ROW(
    target.product_name, target.category, target.subcategory,
    target.brand, target.price, target.cost
) IS DISTINCT FROM ROW(
    EXCLUDED.product_name, EXCLUDED.category, EXCLUDED.subcategory,
    EXCLUDED.brand, EXCLUDED.price, EXCLUDED.cost
);


-- REGION DIMENSION

INSERT INTO warehouse.dim_region (
    city,
    state,
    country
)
SELECT DISTINCT
    COALESCE(NULLIF(BTRIM(o.shipping_city), ''), 'Unknown'),
    COALESCE(NULLIF(BTRIM(o.shipping_state), ''), 'Unknown'),
    'India'
FROM clean.orders AS o

ON CONFLICT (city, state, country)
DO NOTHING;


-- DATE DIMENSION
-- Add missing dates while keeping existing date keys.

WITH source_dates AS (

    SELECT order_date AS date_value
    FROM clean.orders

    UNION ALL

    SELECT return_date AS date_value
    FROM clean.returns

),

bounds AS (

    SELECT
        MIN(date_value) AS min_date,
        MAX(date_value) AS max_date
    FROM source_dates

),

calendar AS (

    SELECT
        GENERATE_SERIES(
            min_date,
            max_date,
            INTERVAL '1 day'
        )::DATE AS full_date
    FROM bounds
    WHERE min_date IS NOT NULL
      AND max_date IS NOT NULL

)

INSERT INTO warehouse.dim_date (
    date_key,
    full_date,
    day_of_month,
    day_of_week,
    day_name,
    month_number,
    month_name,
    quarter,
    year,
    week_of_year,
    is_weekend
)
SELECT
    (
        EXTRACT(YEAR FROM full_date)::INTEGER * 10000
        + EXTRACT(MONTH FROM full_date)::INTEGER * 100
        + EXTRACT(DAY FROM full_date)::INTEGER
    ),
    full_date,
    EXTRACT(DAY FROM full_date)::SMALLINT,
    EXTRACT(ISODOW FROM full_date)::SMALLINT,
    BTRIM(TO_CHAR(full_date, 'FMDay')),
    EXTRACT(MONTH FROM full_date)::SMALLINT,
    BTRIM(TO_CHAR(full_date, 'FMMonth')),
    EXTRACT(QUARTER FROM full_date)::SMALLINT,
    EXTRACT(YEAR FROM full_date)::SMALLINT,
    EXTRACT(WEEK FROM full_date)::SMALLINT,
    EXTRACT(ISODOW FROM full_date) IN (6, 7)
FROM calendar

ON CONFLICT (full_date)
DO NOTHING;