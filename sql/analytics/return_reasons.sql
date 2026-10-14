-- ============================================================
-- RETURN REASONS
-- ============================================================

SELECT
    f.return_reason,

    COUNT(*) AS returned_item_lines,

    SUM(f.quantity) AS returned_units,

    ROUND(
        SUM(f.net_sales),
        2
    ) AS associated_net_sales,

    ROUND(
        SUM(f.profit),
        2
    ) AS associated_profit_before_return_adjustment

FROM warehouse.fact_sales AS f

WHERE f.is_realized_sale = TRUE
  AND f.is_returned = TRUE

GROUP BY
    f.return_reason

ORDER BY
    returned_units DESC,
    returned_item_lines DESC;