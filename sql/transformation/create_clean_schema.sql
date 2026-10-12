-- ============================================================
-- E-Commerce Sales & Customer Analytics Data Platform
-- Clean Layer: Schema and Table Definitions
-- ============================================================

CREATE SCHEMA IF NOT EXISTS clean;


-- ============================================================
-- CUSTOMERS
-- ============================================================

CREATE TABLE IF NOT EXISTS clean.customers (
    customer_id BIGINT PRIMARY KEY,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    email VARCHAR(255),
    gender VARCHAR(20) NOT NULL,
    date_of_birth DATE NOT NULL,
    city VARCHAR(150) NOT NULL,
    state VARCHAR(100) NOT NULL,
    country VARCHAR(100) NOT NULL,
    signup_date DATE NOT NULL,

    CHECK (date_of_birth <= signup_date)
);


-- ============================================================
-- PRODUCTS
-- ============================================================

CREATE TABLE IF NOT EXISTS clean.products (
    product_id BIGINT PRIMARY KEY,
    product_name VARCHAR(255) NOT NULL,
    category VARCHAR(100) NOT NULL,
    subcategory VARCHAR(100) NOT NULL,
    brand VARCHAR(150) NOT NULL,
    price NUMERIC(12, 2) NOT NULL,
    cost NUMERIC(12, 2) NOT NULL,

    CHECK (price > 0),
    CHECK (cost >= 0),
    CHECK (price >= cost)
);


-- ============================================================
-- ORDERS
-- ============================================================

CREATE TABLE IF NOT EXISTS clean.orders (
    order_id BIGINT PRIMARY KEY,
    customer_id BIGINT NOT NULL,
    order_date DATE NOT NULL,
    order_status VARCHAR(50) NOT NULL,
    payment_method VARCHAR(50) NOT NULL,
    shipping_city VARCHAR(150) NOT NULL,
    shipping_state VARCHAR(100) NOT NULL,

    CONSTRAINT fk_clean_orders_customer
        FOREIGN KEY (customer_id)
        REFERENCES clean.customers(customer_id),

    CHECK (
        order_status IN (
            'Delivered',
            'Shipped',
            'Processing',
            'Cancelled'
        )
    ),

    CHECK (
        payment_method IN (
            'UPI',
            'Credit Card',
            'Debit Card',
            'Net Banking',
            'COD'
        )
    )
);


-- ============================================================
-- ORDER ITEMS
-- ============================================================

CREATE TABLE IF NOT EXISTS clean.order_items (
    item_id BIGINT PRIMARY KEY,
    order_id BIGINT NOT NULL,
    product_id BIGINT NOT NULL,
    quantity INTEGER NOT NULL,
    unit_price NUMERIC(12, 2) NOT NULL,
    discount NUMERIC(5, 4) NOT NULL,

    CONSTRAINT fk_clean_items_order
        FOREIGN KEY (order_id)
        REFERENCES clean.orders(order_id),

    CONSTRAINT fk_clean_items_product
        FOREIGN KEY (product_id)
        REFERENCES clean.products(product_id),

    CONSTRAINT uq_clean_order_product
        UNIQUE (order_id, product_id),

    CHECK (quantity > 0),
    CHECK (unit_price > 0),
    CHECK (discount BETWEEN 0 AND 1)
);


-- ============================================================
-- RETURNS
-- ============================================================

CREATE TABLE IF NOT EXISTS clean.returns (
    return_id BIGINT PRIMARY KEY,
    order_id BIGINT NOT NULL,
    product_id BIGINT NOT NULL,
    return_date DATE NOT NULL,
    return_reason VARCHAR(100) NOT NULL,

    CONSTRAINT fk_clean_returns_order_item
        FOREIGN KEY (order_id, product_id)
        REFERENCES clean.order_items(order_id, product_id)
);