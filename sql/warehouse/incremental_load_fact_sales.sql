-- ============================================================
-- INCREMENTAL FACT LOAD
-- Grain: one row per clean order item
-- ============================================================

WITH returns_per_item AS (

    SELECT DISTINCT ON (
        order_id,
        product_id
    )
        order_id,
        product_id,
        return_date,
        return_reason

    FROM clean.returns

    ORDER BY
        order_id,
        product_id,
        return_date DESC,
        return_id DESC

),

calculated_sales AS (

    SELECT
        o.order_id,
        oi.item_id,

        dc.customer_key,
        dp.product_key,
        dd_order.date_key AS order_date_key,
        dr.region_key,

        o.order_status,
        o.payment_method,

        oi.quantity,
        oi.unit_price,
        oi.discount AS discount_rate,

        ROUND(
            oi.quantity * oi.unit_price,
            2
        )::NUMERIC(14, 2) AS gross_sales,

        ROUND(
            oi.quantity * oi.unit_price * oi.discount,
            2
        )::NUMERIC(14, 2) AS discount_amount,

        p.cost AS unit_cost,

        ROUND(
            oi.quantity * p.cost,
            2
        )::NUMERIC(14, 2) AS total_cost,

        dd_return.date_key AS return_date_key,
        r.return_reason

    FROM clean.order_items AS oi

    INNER JOIN clean.orders AS o
        ON o.order_id = oi.order_id

    INNER JOIN clean.products AS p
        ON p.product_id = oi.product_id

    INNER JOIN warehouse.dim_customer AS dc
        ON dc.customer_id = o.customer_id

    INNER JOIN warehouse.dim_product AS dp
        ON dp.product_id = oi.product_id

    INNER JOIN warehouse.dim_date AS dd_order
        ON dd_order.full_date = o.order_date

    INNER JOIN warehouse.dim_region AS dr
        ON dr.city = COALESCE(
            NULLIF(BTRIM(o.shipping_city), ''),
            'Unknown'
        )
        AND dr.state = COALESCE(
            NULLIF(BTRIM(o.shipping_state), ''),
            'Unknown'
        )
        AND dr.country = 'India'

    LEFT JOIN returns_per_item AS r
        ON r.order_id = oi.order_id
       AND r.product_id = oi.product_id

    LEFT JOIN warehouse.dim_date AS dd_return
        ON dd_return.full_date = r.return_date

)

INSERT INTO warehouse.fact_sales AS target (
    order_id,
    item_id,
    customer_key,
    product_key,
    order_date_key,
    region_key,

    order_status,
    payment_method,

    quantity,
    unit_price,
    discount_rate,

    gross_sales,
    discount_amount,
    net_sales,

    unit_cost,
    total_cost,
    profit,

    is_realized_sale,
    is_returned,
    return_date_key,
    return_reason
)

SELECT
    order_id,
    item_id,
    customer_key,
    product_key,
    order_date_key,
    region_key,

    order_status,
    payment_method,

    quantity,
    unit_price,
    discount_rate,

    gross_sales,
    discount_amount,

    (
        gross_sales - discount_amount
    )::NUMERIC(14, 2),

    unit_cost,
    total_cost,

    (
        gross_sales - discount_amount - total_cost
    )::NUMERIC(14, 2),

    (order_status = 'Delivered'),

    (return_date_key IS NOT NULL),

    return_date_key,
    return_reason

FROM calculated_sales

ON CONFLICT (item_id)
DO UPDATE SET
    order_id = EXCLUDED.order_id,
    customer_key = EXCLUDED.customer_key,
    product_key = EXCLUDED.product_key,
    order_date_key = EXCLUDED.order_date_key,
    region_key = EXCLUDED.region_key,

    order_status = EXCLUDED.order_status,
    payment_method = EXCLUDED.payment_method,

    quantity = EXCLUDED.quantity,
    unit_price = EXCLUDED.unit_price,
    discount_rate = EXCLUDED.discount_rate,

    gross_sales = EXCLUDED.gross_sales,
    discount_amount = EXCLUDED.discount_amount,
    net_sales = EXCLUDED.net_sales,

    unit_cost = EXCLUDED.unit_cost,
    total_cost = EXCLUDED.total_cost,
    profit = EXCLUDED.profit,

    is_realized_sale = EXCLUDED.is_realized_sale,
    is_returned = EXCLUDED.is_returned,
    return_date_key = EXCLUDED.return_date_key,
    return_reason = EXCLUDED.return_reason

WHERE ROW(
    target.order_id,
    target.customer_key,
    target.product_key,
    target.order_date_key,
    target.region_key,
    target.order_status,
    target.payment_method,
    target.quantity,
    target.unit_price,
    target.discount_rate,
    target.gross_sales,
    target.discount_amount,
    target.net_sales,
    target.unit_cost,
    target.total_cost,
    target.profit,
    target.is_realized_sale,
    target.is_returned,
    target.return_date_key,
    target.return_reason
) IS DISTINCT FROM ROW(
    EXCLUDED.order_id,
    EXCLUDED.customer_key,
    EXCLUDED.product_key,
    EXCLUDED.order_date_key,
    EXCLUDED.region_key,
    EXCLUDED.order_status,
    EXCLUDED.payment_method,
    EXCLUDED.quantity,
    EXCLUDED.unit_price,
    EXCLUDED.discount_rate,
    EXCLUDED.gross_sales,
    EXCLUDED.discount_amount,
    EXCLUDED.net_sales,
    EXCLUDED.unit_cost,
    EXCLUDED.total_cost,
    EXCLUDED.profit,
    EXCLUDED.is_realized_sale,
    EXCLUDED.is_returned,
    EXCLUDED.return_date_key,
    EXCLUDED.return_reason
);