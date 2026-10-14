-- ============================================================
-- RETURN ANALYSIS SUMMARY
-- ============================================================

SELECT
    COUNT(*) AS all_fact_items,

    COUNT(*) FILTER (
        WHERE is_realized_sale = TRUE
    ) AS delivered_items,

    COUNT(*) FILTER (
        WHERE is_realized_sale = TRUE
          AND is_returned = TRUE
    ) AS returned_delivered_items,

    SUM(quantity) FILTER (
        WHERE is_realized_sale = TRUE
    ) AS delivered_units,

    SUM(quantity) FILTER (
        WHERE is_realized_sale = TRUE
          AND is_returned = TRUE
    ) AS returned_delivered_units,

    ROUND(
        100.0 * COUNT(*) FILTER (
            WHERE is_realized_sale = TRUE
              AND is_returned = TRUE
        )
        / NULLIF(
            COUNT(*) FILTER (
                WHERE is_realized_sale = TRUE
            ),
            0
        ),
        2
    ) AS returned_item_rate_pct,

    ROUND(
        100.0 * SUM(quantity) FILTER (
            WHERE is_realized_sale = TRUE
              AND is_returned = TRUE
        )
        / NULLIF(
            SUM(quantity) FILTER (
                WHERE is_realized_sale = TRUE
            ),
            0
        ),
        2
    ) AS returned_unit_rate_pct

FROM warehouse.fact_sales;