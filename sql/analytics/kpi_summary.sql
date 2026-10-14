-- ============================================================
-- OVERALL E-COMMERCE KPI SUMMARY
-- ============================================================

WITH metrics AS (
    SELECT
        COUNT(DISTINCT order_id)
            FILTER (
                WHERE is_realized_sale = TRUE
            ) AS delivered_orders,

        COUNT(*)
            FILTER (
                WHERE is_realized_sale = TRUE
            ) AS delivered_order_items,

        SUM(quantity)
            FILTER (
                WHERE is_realized_sale = TRUE
            ) AS units_sold,

        SUM(gross_sales)
            FILTER (
                WHERE is_realized_sale = TRUE
            ) AS gross_sales,

        SUM(discount_amount)
            FILTER (
                WHERE is_realized_sale = TRUE
            ) AS total_discount,

        SUM(net_sales)
            FILTER (
                WHERE is_realized_sale = TRUE
            ) AS net_sales_before_returns,

        SUM(net_sales)
            FILTER (
                WHERE is_realized_sale = TRUE
                  AND is_returned = FALSE
            ) AS net_sales_after_returns,

        SUM(profit)
            FILTER (
                WHERE is_realized_sale = TRUE
                  AND is_returned = FALSE
            ) AS retained_profit,

        COUNT(*)
            FILTER (
                WHERE is_realized_sale = TRUE
                  AND is_returned = TRUE
            ) AS returned_items

    FROM warehouse.fact_sales
)

SELECT
    COALESCE(delivered_orders, 0) AS delivered_orders,

    COALESCE(delivered_order_items, 0)
        AS delivered_order_items,

    COALESCE(units_sold, 0) AS units_sold,

    ROUND(
        COALESCE(gross_sales, 0),
        2
    ) AS gross_sales,

    ROUND(
        COALESCE(total_discount, 0),
        2
    ) AS total_discount,

    ROUND(
        COALESCE(net_sales_before_returns, 0),
        2
    ) AS net_sales_before_returns,

    ROUND(
        COALESCE(net_sales_after_returns, 0),
        2
    ) AS net_sales_after_returns,

    ROUND(
        COALESCE(retained_profit, 0),
        2
    ) AS retained_profit,

    ROUND(
        100.0 * returned_items
        / NULLIF(delivered_order_items, 0),
        2
    ) AS returned_item_rate_pct,

    ROUND(
        net_sales_before_returns
        / NULLIF(delivered_orders, 0),
        2
    ) AS average_order_value

FROM metrics;