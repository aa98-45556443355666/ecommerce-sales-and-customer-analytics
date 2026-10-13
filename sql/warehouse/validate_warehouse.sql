-- ============================================================
-- 1. ROW COUNTS
-- ============================================================

SELECT 'dim_customer' AS table_name, COUNT(*) AS row_count
FROM warehouse.dim_customer

UNION ALL

SELECT 'dim_product', COUNT(*)
FROM warehouse.dim_product

UNION ALL

SELECT 'dim_date', COUNT(*)
FROM warehouse.dim_date

UNION ALL

SELECT 'dim_region', COUNT(*)
FROM warehouse.dim_region

UNION ALL

SELECT 'fact_sales', COUNT(*)
FROM warehouse.fact_sales;


-- ============================================================
-- 2. FACT ROW COUNT VS CLEAN ORDER ITEMS
-- ============================================================

SELECT
    (SELECT COUNT(*)
     FROM clean.order_items) AS clean_item_count,

    (SELECT COUNT(*)
     FROM warehouse.fact_sales) AS fact_sales_count,

    (
        (SELECT COUNT(*) FROM clean.order_items)
        -
        (SELECT COUNT(*) FROM warehouse.fact_sales)
    ) AS row_difference;


-- ============================================================
-- 3. DUPLICATE FACT ITEMS
-- ============================================================

SELECT item_id, COUNT(*) AS duplicate_count
FROM warehouse.fact_sales
GROUP BY item_id
HAVING COUNT(*) > 1;


-- ============================================================
-- 4. SALES CALCULATION CHECK
-- ============================================================

SELECT COUNT(*) AS invalid_calculation_rows
FROM warehouse.fact_sales
WHERE net_sales <> gross_sales - discount_amount
   OR profit <> net_sales - total_cost;


-- ============================================================
-- 5. MONTHLY REALIZED REVENUE
-- ============================================================

SELECT
    d.year,
    d.month_number,
    d.month_name,

    ROUND(
        SUM(f.net_sales),
        2
    ) AS realized_revenue,

    ROUND(
        SUM(f.profit),
        2
    ) AS realized_profit

FROM warehouse.fact_sales AS f

JOIN warehouse.dim_date AS d
    ON d.date_key = f.order_date_key

WHERE f.is_realized_sale = TRUE

GROUP BY
    d.year,
    d.month_number,
    d.month_name

ORDER BY
    d.year,
    d.month_number;


-- ============================================================
-- 6. RETURN RATE
-- ============================================================

SELECT
    COUNT(*) AS total_order_items,

    COUNT(*) FILTER (
        WHERE is_returned = TRUE
    ) AS returned_items,

    ROUND(
        100.0 * COUNT(*) FILTER (
            WHERE is_returned = TRUE
        ) / NULLIF(COUNT(*), 0),
        2
    ) AS return_rate_percentage

FROM warehouse.fact_sales;


-- ============================================================
-- 7. REVENUE BY REGION
-- ============================================================

SELECT
    r.state,
    r.city,

    ROUND(
        SUM(f.net_sales),
        2
    ) AS realized_revenue

FROM warehouse.fact_sales AS f

INNER JOIN warehouse.dim_region AS r
    ON r.region_key = f.region_key

WHERE f.is_realized_sale = TRUE

GROUP BY
    r.state,
    r.city

ORDER BY
    realized_revenue DESC

LIMIT 20;