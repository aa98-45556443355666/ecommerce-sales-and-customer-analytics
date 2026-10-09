-- ============================================================
-- STAGING VALIDATION QUERIES
-- ============================================================
-- Check that the staging schema exists.

SELECT schema_name
FROM information_schema.schemata
WHERE schema_name = 'staging';


-- ============================================================
-- TABLE COUNTS
-- ============================================================

SELECT COUNT(*) AS customer_rows
FROM staging.customers;

SELECT COUNT(*) AS product_rows
FROM staging.products;

SELECT COUNT(*) AS order_rows
FROM staging.orders;

SELECT COUNT(*) AS order_item_rows
FROM staging.order_items;

SELECT COUNT(*) AS return_rows
FROM staging.returns;


-- ============================================================
-- TABLE EXISTENCE
-- ============================================================

SELECT
    table_schema,
    table_name
FROM information_schema.tables
WHERE table_schema = 'staging'
ORDER BY table_name;


-- ============================================================
-- CUSTOMER COLUMNS
-- ============================================================

SELECT
    column_name,
    data_type
FROM information_schema.columns
WHERE table_schema = 'staging'
  AND table_name = 'customers'
ORDER BY ordinal_position;


-- ============================================================
-- PRODUCT COLUMNS
-- ============================================================

SELECT
    column_name,
    data_type
FROM information_schema.columns
WHERE table_schema = 'staging'
  AND table_name = 'products'
ORDER BY ordinal_position;


-- ============================================================
-- ORDER COLUMNS
-- ============================================================

SELECT
    column_name,
    data_type
FROM information_schema.columns
WHERE table_schema = 'staging'
  AND table_name = 'orders'
ORDER BY ordinal_position;


-- ============================================================
-- ORDER ITEM COLUMNS
-- ============================================================

SELECT
    column_name,
    data_type
FROM information_schema.columns
WHERE table_schema = 'staging'
  AND table_name = 'order_items'
ORDER BY ordinal_position;


-- ============================================================
-- RETURN COLUMNS
-- ============================================================

SELECT
    column_name,
    data_type
FROM information_schema.columns
WHERE table_schema = 'staging'
  AND table_name = 'returns'
ORDER BY ordinal_position;