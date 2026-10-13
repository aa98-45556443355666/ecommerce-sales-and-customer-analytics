-- ============================================================
-- LOAD FACT SALES
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

INSERT INTO warehouse.fact_sales (
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
    )::NUMERIC(14, 2) AS net_sales,

    unit_cost,
    total_cost,

    (
        gross_sales - discount_amount - total_cost
    )::NUMERIC(14, 2) AS profit,

    (order_status = 'Delivered') AS is_realized_sale,

    (return_date_key IS NOT NULL) AS is_returned,

    return_date_key,
    return_reason

FROM calculated_sales;