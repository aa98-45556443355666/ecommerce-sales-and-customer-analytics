-- ============================================================
-- LOAD DIMENSION TABLES
-- ============================================================

TRUNCATE TABLE
    warehouse.fact_sales,
    warehouse.dim_customer,
    warehouse.dim_product,
    warehouse.dim_date,
    warehouse.dim_region
RESTART IDENTITY CASCADE;

-- ============================================================
-- 1. CUSTOMER DIMENSION
-- ============================================================

INSERT INTO warehouse.dim_customer (
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
    country = EXCLUDED.country;


-- ============================================================
-- 2. PRODUCT DIMENSION
-- ============================================================

INSERT INTO warehouse.dim_product (
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
    cost = EXCLUDED.cost;


-- ============================================================
-- 3. REGION DIMENSION
-- ============================================================

INSERT INTO warehouse.dim_region (
    city,
    state,
    country
)
SELECT DISTINCT
    COALESCE(
        NULLIF(BTRIM(shipping_city), ''),
        'Unknown'
    ) AS city,

    COALESCE(
        NULLIF(BTRIM(shipping_state), ''),
        'Unknown'
    ) AS state,

    'India' AS country

FROM clean.orders
WHERE TRUE

ON CONFLICT (city, state, country)
DO NOTHING;

-- ============================================================
-- 4. DATE DIMENSION
-- ============================================================

WITH source_dates AS (

    SELECT order_date AS date_value
    FROM clean.orders

    UNION ALL

    SELECT return_date AS date_value
    FROM clean.returns

),

date_bounds AS (

    SELECT
        MIN(date_value) AS min_date,
        MAX(date_value) AS max_date
    FROM source_dates

),

calendar AS (

    SELECT
        generate_series(
            min_date,
            max_date,
            INTERVAL '1 day'
        )::DATE AS full_date

    FROM date_bounds

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
    ) AS date_key,

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
DO UPDATE SET
    day_of_month = EXCLUDED.day_of_month,
    day_of_week = EXCLUDED.day_of_week,
    day_name = EXCLUDED.day_name,
    month_number = EXCLUDED.month_number,
    month_name = EXCLUDED.month_name,
    quarter = EXCLUDED.quarter,
    year = EXCLUDED.year,
    week_of_year = EXCLUDED.week_of_year,
    is_weekend = EXCLUDED.is_weekend;