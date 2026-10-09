-- ============================================================
-- E-Commerce Sales & Customer Analytics Data Platform
-- PostgreSQL Staging Tables
-- ============================================================
-- ============================================================
-- CUSTOMERS
-- ============================================================

DROP TABLE IF EXISTS staging.customers;

CREATE TABLE staging.customers (
    customer_id      BIGINT,
    first_name       VARCHAR(100),
    last_name        VARCHAR(100),
    email            VARCHAR(255),
    gender           VARCHAR(20),
    date_of_birth    DATE,
    city             VARCHAR(150),
    state            VARCHAR(100),
    country          VARCHAR(100),
    signup_date      DATE
);


-- ============================================================
-- PRODUCTS
-- ============================================================

DROP TABLE IF EXISTS staging.products;

CREATE TABLE staging.products (
    product_id       BIGINT,
    product_name     VARCHAR(255),
    category         VARCHAR(100),
    subcategory      VARCHAR(100),
    brand            VARCHAR(150),
    price            NUMERIC(12, 2),
    cost             NUMERIC(12, 2)
);


-- ============================================================
-- ORDERS
-- ============================================================

DROP TABLE IF EXISTS staging.orders;

CREATE TABLE staging.orders (
    order_id         BIGINT,
    customer_id      BIGINT,
    order_date       DATE,
    order_status     VARCHAR(50),
    payment_method   VARCHAR(50),
    shipping_city    VARCHAR(150),
    shipping_state   VARCHAR(100)
);


-- ============================================================
-- ORDER ITEMS
-- ============================================================

DROP TABLE IF EXISTS staging.order_items;

CREATE TABLE staging.order_items (
    item_id          BIGINT,
    order_id         BIGINT,
    product_id       BIGINT,
    quantity         INTEGER,
    unit_price       NUMERIC(12, 2),
    discount         NUMERIC(5, 4)
);


-- ============================================================
-- RETURNS
-- ============================================================

DROP TABLE IF EXISTS staging.returns;

CREATE TABLE staging.returns (
    return_id        BIGINT,
    order_id         BIGINT,
    product_id       BIGINT,
    return_date      DATE,
    return_reason    VARCHAR(100)
);