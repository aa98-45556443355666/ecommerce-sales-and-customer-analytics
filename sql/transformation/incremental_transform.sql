-- ============================================================
-- INCREMENTAL STAGING -> CLEAN TRANSFORMATION
-- Insert new records; update only changed records.
-- Source deletions are not propagated in this version.
-- ============================================================


-- ============================================================
-- 1. CUSTOMERS
-- ============================================================

INSERT INTO clean.customers AS target (
    customer_id,
    first_name,
    last_name,
    email,
    gender,
    date_of_birth,
    city,
    state,
    country,
    signup_date
)
SELECT DISTINCT ON (c.customer_id)
    c.customer_id,
    BTRIM(c.first_name),
    BTRIM(c.last_name),
    LOWER(NULLIF(BTRIM(c.email), '')),
    COALESCE(NULLIF(INITCAP(BTRIM(c.gender)), ''), 'Unknown'),
    c.date_of_birth,
    COALESCE(NULLIF(BTRIM(c.city), ''), 'Unknown'),
    COALESCE(NULLIF(BTRIM(c.state), ''), 'Unknown'),
    COALESCE(NULLIF(BTRIM(c.country), ''), 'India'),
    c.signup_date
FROM staging.customers AS c
WHERE c.customer_id IS NOT NULL
  AND NULLIF(BTRIM(c.first_name), '') IS NOT NULL
  AND NULLIF(BTRIM(c.last_name), '') IS NOT NULL
  AND c.date_of_birth IS NOT NULL
  AND c.signup_date IS NOT NULL
  AND c.date_of_birth <= c.signup_date
  AND c.signup_date <= CURRENT_DATE
ORDER BY
    c.customer_id,
    (NULLIF(BTRIM(c.email), '') IS NULL),
    c.signup_date DESC NULLS LAST,
    c.first_name,
    c.last_name

ON CONFLICT (customer_id)
DO UPDATE SET
    first_name = EXCLUDED.first_name,
    last_name = EXCLUDED.last_name,
    email = EXCLUDED.email,
    gender = EXCLUDED.gender,
    date_of_birth = EXCLUDED.date_of_birth,
    city = EXCLUDED.city,
    state = EXCLUDED.state,
    country = EXCLUDED.country,
    signup_date = EXCLUDED.signup_date

WHERE ROW(
    target.first_name,
    target.last_name,
    target.email,
    target.gender,
    target.date_of_birth,
    target.city,
    target.state,
    target.country,
    target.signup_date
) IS DISTINCT FROM ROW(
    EXCLUDED.first_name,
    EXCLUDED.last_name,
    EXCLUDED.email,
    EXCLUDED.gender,
    EXCLUDED.date_of_birth,
    EXCLUDED.city,
    EXCLUDED.state,
    EXCLUDED.country,
    EXCLUDED.signup_date
);


-- ============================================================
-- 2. PRODUCTS
-- ============================================================

INSERT INTO clean.products AS target (
    product_id,
    product_name,
    category,
    subcategory,
    brand,
    price,
    cost
)
SELECT DISTINCT ON (p.product_id)
    p.product_id,
    BTRIM(p.product_name),
    COALESCE(NULLIF(INITCAP(BTRIM(p.category)), ''), 'Unknown'),
    COALESCE(NULLIF(BTRIM(p.subcategory), ''), 'Unknown'),
    COALESCE(NULLIF(BTRIM(p.brand), ''), 'Unknown'),
    p.price,
    p.cost
FROM staging.products AS p
WHERE p.product_id IS NOT NULL
  AND NULLIF(BTRIM(p.product_name), '') IS NOT NULL
  AND p.price IS NOT NULL
  AND p.cost IS NOT NULL
  AND p.price > 0
  AND p.cost >= 0
  AND p.price >= p.cost
ORDER BY
    p.product_id,
    (NULLIF(BTRIM(p.category), '') IS NULL),
    p.product_name

ON CONFLICT (product_id)
DO UPDATE SET
    product_name = EXCLUDED.product_name,
    category = EXCLUDED.category,
    subcategory = EXCLUDED.subcategory,
    brand = EXCLUDED.brand,
    price = EXCLUDED.price,
    cost = EXCLUDED.cost

WHERE ROW(
    target.product_name,
    target.category,
    target.subcategory,
    target.brand,
    target.price,
    target.cost
) IS DISTINCT FROM ROW(
    EXCLUDED.product_name,
    EXCLUDED.category,
    EXCLUDED.subcategory,
    EXCLUDED.brand,
    EXCLUDED.price,
    EXCLUDED.cost
);


-- ============================================================
-- 3. ORDERS
-- ============================================================

INSERT INTO clean.orders AS target (
    order_id,
    customer_id,
    order_date,
    order_status,
    payment_method,
    shipping_city,
    shipping_state
)
SELECT DISTINCT ON (o.order_id)
    o.order_id,
    o.customer_id,
    o.order_date,
    BTRIM(o.order_status),
    BTRIM(o.payment_method),
    COALESCE(NULLIF(BTRIM(o.shipping_city), ''), 'Unknown'),
    COALESCE(NULLIF(BTRIM(o.shipping_state), ''), 'Unknown')
FROM staging.orders AS o

INNER JOIN clean.customers AS c
    ON c.customer_id = o.customer_id

WHERE o.order_id IS NOT NULL
  AND o.order_date IS NOT NULL
  AND o.order_date <= CURRENT_DATE
  AND o.order_status IN (
      'Delivered', 'Shipped', 'Processing', 'Cancelled'
  )
  AND o.payment_method IN (
      'UPI', 'Credit Card', 'Debit Card', 'Net Banking', 'COD'
  )

ORDER BY
    o.order_id,
    o.order_date DESC NULLS LAST,
    o.customer_id

ON CONFLICT (order_id)
DO UPDATE SET
    customer_id = EXCLUDED.customer_id,
    order_date = EXCLUDED.order_date,
    order_status = EXCLUDED.order_status,
    payment_method = EXCLUDED.payment_method,
    shipping_city = EXCLUDED.shipping_city,
    shipping_state = EXCLUDED.shipping_state

WHERE ROW(
    target.customer_id,
    target.order_date,
    target.order_status,
    target.payment_method,
    target.shipping_city,
    target.shipping_state
) IS DISTINCT FROM ROW(
    EXCLUDED.customer_id,
    EXCLUDED.order_date,
    EXCLUDED.order_status,
    EXCLUDED.payment_method,
    EXCLUDED.shipping_city,
    EXCLUDED.shipping_state
);


-- ============================================================
-- 4. ORDER ITEMS
-- Grain: one clean row per order/product combination.
-- Existing item identity is preserved on conflict.
-- ============================================================

WITH valid_items AS (

    SELECT DISTINCT ON (
        oi.order_id,
        oi.product_id
    )
        oi.item_id,
        oi.order_id,
        oi.product_id,
        oi.quantity,
        oi.unit_price,
        oi.discount

    FROM staging.order_items AS oi

    INNER JOIN clean.orders AS o
        ON o.order_id = oi.order_id

    INNER JOIN clean.products AS p
        ON p.product_id = oi.product_id

    WHERE oi.item_id IS NOT NULL
      AND oi.quantity > 0
      AND oi.unit_price > 0
      AND oi.discount BETWEEN 0 AND 1
      AND ROUND(oi.unit_price, 2) = ROUND(p.price, 2)

    ORDER BY
        oi.order_id,
        oi.product_id,
        oi.item_id
)

INSERT INTO clean.order_items AS target (
    item_id,
    order_id,
    product_id,
    quantity,
    unit_price,
    discount
)
SELECT
    item_id,
    order_id,
    product_id,
    quantity,
    unit_price,
    discount
FROM valid_items

ON CONFLICT (order_id, product_id)
DO UPDATE SET
    quantity = EXCLUDED.quantity,
    unit_price = EXCLUDED.unit_price,
    discount = EXCLUDED.discount

WHERE ROW(
    target.quantity,
    target.unit_price,
    target.discount
) IS DISTINCT FROM ROW(
    EXCLUDED.quantity,
    EXCLUDED.unit_price,
    EXCLUDED.discount
);


-- ============================================================
-- 5. RETURNS
-- ============================================================

INSERT INTO clean.returns AS target (
    return_id,
    order_id,
    product_id,
    return_date,
    return_reason
)
SELECT DISTINCT ON (r.return_id)
    r.return_id,
    r.order_id,
    r.product_id,
    r.return_date,
    BTRIM(r.return_reason)

FROM staging.returns AS r

INNER JOIN clean.order_items AS oi
    ON oi.order_id = r.order_id
   AND oi.product_id = r.product_id

INNER JOIN clean.orders AS o
    ON o.order_id = r.order_id

WHERE r.return_id IS NOT NULL
  AND r.return_date IS NOT NULL
  AND r.return_date >= o.order_date
  AND NULLIF(BTRIM(r.return_reason), '') IS NOT NULL

ORDER BY
    r.return_id,
    r.return_date DESC,
    r.order_id,
    r.product_id

ON CONFLICT (return_id)
DO UPDATE SET
    order_id = EXCLUDED.order_id,
    product_id = EXCLUDED.product_id,
    return_date = EXCLUDED.return_date,
    return_reason = EXCLUDED.return_reason

WHERE ROW(
    target.order_id,
    target.product_id,
    target.return_date,
    target.return_reason
) IS DISTINCT FROM ROW(
    EXCLUDED.order_id,
    EXCLUDED.product_id,
    EXCLUDED.return_date,
    EXCLUDED.return_reason
);