# Analytics SQL

This directory contains analytical SQL queries built on top of
the PostgreSQL star-schema warehouse.

## Reports

- `kpi_summary.sql`: Overall sales and business KPIs.
- `monthly_sales_performance.sql`: Monthly revenue and profit trends.
- `product_performance.sql`: Product-level sales and returns.
- `customer_lifetime_value.sql`: Customer spending and order history.
- `customer_segmentation.sql`: Relative RFM-style customer segments.
- `regional_performance.sql`: Sales by state and city.
- `return_analysis.sql`: Return rates at line and unit level.
- `return_reasons.sql`: Most frequent return reasons.
- `payment_method_analysis.sql`: Sales by payment method.
- `order_status_analysis.sql`: Order status distribution.
- `sales_by_weekday.sql`: Weekday and weekend performance.

## Metric Definitions

- Gross sales = quantity multiplied by unit price.
- Discount amount = gross sales multiplied by discount rate.
- Net sales before returns = gross sales minus discounts.
- Net sales after returns = net sales before returns excluding
  returned item lines.
- Retained profit = net sales after returns minus the original
  product cost of the retained items.
- Realized sale = an order item belonging to a Delivered order.
- Return rate = returned items divided by delivered item lines,
  unless the query explicitly measures units.

## Data Model

All reports use `warehouse.fact_sales` and its related dimensions.

The fact table grain is one cleaned order item per row.

## Limitations

The synthetic dataset does not model actual refund transactions,
reverse-logistics costs, or the financial recovery of returned
inventory. Return-adjusted metrics are therefore estimates based
on returned item flags.