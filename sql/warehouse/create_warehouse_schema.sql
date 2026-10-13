-- ============================================================
-- E-Commerce Sales & Customer Analytics Data Platform
-- Star Schema: DDL
-- ============================================================

CREATE SCHEMA IF NOT EXISTS warehouse;

-- ============================================================
-- DIMENSION: CUSTOMER
-- ============================================================

CREATE TABLE IF NOT EXISTS warehouse.dim_customer (
    customer_key BIGSERIAL PRIMARY KEY,
    customer_id BIGINT NOT NULL UNIQUE,

    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    email VARCHAR(255),
    gender VARCHAR(20) NOT NULL,
    date_of_birth DATE NOT NULL,
    signup_date DATE NOT NULL,
    city VARCHAR(150) NOT NULL,
    state VARCHAR(100) NOT NULL,
    country VARCHAR(100) NOT NULL
);


-- ============================================================
-- DIMENSION: PRODUCT
-- ============================================================

CREATE TABLE IF NOT EXISTS warehouse.dim_product (
    product_key BIGSERIAL PRIMARY KEY,
    product_id BIGINT NOT NULL UNIQUE,

    product_name VARCHAR(255) NOT NULL,
    category VARCHAR(100) NOT NULL,
    subcategory VARCHAR(100) NOT NULL,
    brand VARCHAR(150) NOT NULL,

    price NUMERIC(12, 2) NOT NULL,
    cost NUMERIC(12, 2) NOT NULL,

    CHECK (price > 0),
    CHECK (cost >= 0)
);


-- ============================================================
-- DIMENSION: DATE
-- ============================================================

CREATE TABLE IF NOT EXISTS warehouse.dim_date (
    date_key INTEGER PRIMARY KEY,
    full_date DATE NOT NULL UNIQUE,

    day_of_month SMALLINT NOT NULL,
    day_of_week SMALLINT NOT NULL,
    day_name VARCHAR(9) NOT NULL,

    month_number SMALLINT NOT NULL,
    month_name VARCHAR(9) NOT NULL,

    quarter SMALLINT NOT NULL,
    year SMALLINT NOT NULL,
    week_of_year SMALLINT NOT NULL,

    is_weekend BOOLEAN NOT NULL,

    CHECK (day_of_week BETWEEN 1 AND 7),
    CHECK (month_number BETWEEN 1 AND 12),
    CHECK (quarter BETWEEN 1 AND 4)
);

-- ============================================================
-- DIMENSION: REGION
-- ============================================================

CREATE TABLE IF NOT EXISTS warehouse.dim_region (
    region_key BIGSERIAL PRIMARY KEY,

    city VARCHAR(150) NOT NULL,
    state VARCHAR(100) NOT NULL,
    country VARCHAR(100) NOT NULL,

    CONSTRAINT uq_dim_region
        UNIQUE (city, state, country)
);


-- ============================================================
-- FACT: SALES
-- ============================================================

CREATE TABLE IF NOT EXISTS warehouse.fact_sales (
    sales_key BIGSERIAL PRIMARY KEY,

    order_id BIGINT NOT NULL,
    item_id BIGINT NOT NULL UNIQUE,

    customer_key BIGINT NOT NULL,
    product_key BIGINT NOT NULL,
    order_date_key INTEGER NOT NULL,
    region_key BIGINT NOT NULL,

    order_status VARCHAR(50) NOT NULL,
    payment_method VARCHAR(50) NOT NULL,

    quantity INTEGER NOT NULL,

    unit_price NUMERIC(12, 2) NOT NULL,
    discount_rate NUMERIC(5, 4) NOT NULL,

    gross_sales NUMERIC(14, 2) NOT NULL,
    discount_amount NUMERIC(14, 2) NOT NULL,
    net_sales NUMERIC(14, 2) NOT NULL,

    unit_cost NUMERIC(12, 2) NOT NULL,
    total_cost NUMERIC(14, 2) NOT NULL,
    profit NUMERIC(14, 2) NOT NULL,

    is_realized_sale BOOLEAN NOT NULL,

    is_returned BOOLEAN NOT NULL DEFAULT FALSE,
    return_date_key INTEGER,
    return_reason VARCHAR(100),

    CONSTRAINT fk_fact_customer
        FOREIGN KEY (customer_key)
        REFERENCES warehouse.dim_customer(customer_key),

    CONSTRAINT fk_fact_product
        FOREIGN KEY (product_key)
        REFERENCES warehouse.dim_product(product_key),

    CONSTRAINT fk_fact_order_date
        FOREIGN KEY (order_date_key)
        REFERENCES warehouse.dim_date(date_key),

    CONSTRAINT fk_fact_region
        FOREIGN KEY (region_key)
        REFERENCES warehouse.dim_region(region_key),

    CONSTRAINT fk_fact_return_date
        FOREIGN KEY (return_date_key)
        REFERENCES warehouse.dim_date(date_key),

    CHECK (quantity > 0),
    CHECK (unit_price > 0),
    CHECK (discount_rate BETWEEN 0 AND 1),

    CHECK (gross_sales >= 0),
    CHECK (discount_amount >= 0),
    CHECK (discount_amount <= gross_sales),
    CHECK (net_sales >= 0),
    CHECK (total_cost >= 0),

    CHECK (
        net_sales = gross_sales - discount_amount
    ),

    CHECK (
        profit = net_sales - total_cost
    ),

    CHECK (
        (
            is_returned = TRUE
            AND return_date_key IS NOT NULL
            AND return_reason IS NOT NULL
        )
        OR
        (
            is_returned = FALSE
            AND return_date_key IS NULL
            AND return_reason IS NULL
        )
    )
);


-- ============================================================
-- FACT TABLE INDEXES
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_fact_sales_customer
    ON warehouse.fact_sales(customer_key);

CREATE INDEX IF NOT EXISTS idx_fact_sales_product
    ON warehouse.fact_sales(product_key);

CREATE INDEX IF NOT EXISTS idx_fact_sales_date
    ON warehouse.fact_sales(order_date_key);

CREATE INDEX IF NOT EXISTS idx_fact_sales_region
    ON warehouse.fact_sales(region_key);

CREATE INDEX IF NOT EXISTS idx_fact_sales_status
    ON warehouse.fact_sales(order_status);