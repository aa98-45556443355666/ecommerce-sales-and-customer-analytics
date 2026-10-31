# Data Dictionary

## 1. Purpose

This document describes the major data entities and database layers used in the Ecommerce Sales and Customer Analytics project.

It documents the business purpose, grain and important keys of the datasets used throughout the pipeline.

The SQL DDL and transformation scripts remain the source of truth for the complete physical column definitions.

## 2. Source Data

The project uses the following raw CSV datasets:

| Source File | Business Purpose |
|---|---|
| customers.csv | Customer information |
| products.csv | Product catalog |
| orders.csv | Order information |
| order_items.csv | Products associated with orders |
| returns.csv | Product return records |

Raw files are stored in `data/raw/` and are not committed to the repository.

## 3. Staging Layer

Schema: `staging`

Purpose:
- Preserve ingested source data.
- Provide a structured landing layer.
- Support validation before transformation.
- Enable incremental file ingestion.

The staging tables correspond to the source datasets.

### ETL Control

Control table:

`etl_control.source_file_state`

Purpose:
- Maintain source-file processing state.
- Support file-hash-based change detection.
- Track previously processed source files.

The actual control-table columns are defined in:

`sql/control/create_etl_control.sql`

## 4. Clean Layer

Schema: `clean`

The clean layer stores standardized data used by warehouse transformations.

Important entities:

| Table | Description |
|---|---|
| clean.orders | Cleaned order information |
| clean.products | Cleaned product information |
| clean.returns | Individual return records |

Additional clean entities are defined by the clean-layer SQL scripts.

Important business identifiers:

- `order_id`: identifies an order.
- `customer_id`: identifies a customer.
- `product_id`: identifies a product.
- `return_id`: identifies a return record.

## 5. Data Warehouse

Schema: `warehouse`

The warehouse follows a dimensional modeling approach.

### Dimension Tables

| Table | Key | Description |
|---|---|---|
| dim_customer | customer_key | Customer dimension |
| dim_product | product_key | Product dimension |
| dim_date | date_key | Calendar/date dimension |
| dim_region | region_key | Geographic dimension |

### Fact Table

| Table | Important Foreign Keys | Description |
|---|---|---|
| fact_sales | customer_key, product_key, order_date_key, region_key | Sales-related business measurements |

The exact grain of `fact_sales` is defined by:

`sql/warehouse/load_fact_sales.sql`

Always use that SQL file when interpreting whether a row represents an order, order item or another business event.

## 6. Analytics Layer

Schema: `analytics`

Important views include:

| View | Purpose |
|---|---|
| vw_customer_performance | Customer-level sales and performance metrics |
| vw_customer_segments | Customer segmentation |
| vw_customer_segment_membership | Customer ID to segment mapping |
| vw_return_detail | Row-level return reporting |
| vw_return_reasons | Return reason summary |
| vw_powerbi_sales_fact | Power BI-compatible sales fact export |
| vw_executive_kpis | Executive-level KPI reporting |
| vw_monthly_sales | Monthly sales analysis |
| vw_product_performance | Product-level analytics |
| vw_regional_performance | Regional sales analytics |

Additional analytical views are defined under `sql/analytics/`.

### Customer Segmentation

The project assigns customers to the following segments:

- Champions
- Loyal Customers
- Recent Customers
- At Risk
- Regular Customers
- No Delivered Orders

Segmentation uses three scores:

- Recency score
- Frequency score
- Monetary score

The scoring logic is defined in `vw_customer_segments`.

## 7. Power BI Reporting Exports

Output directory:

`data/processed/powerbi_output/`

### Core Model Files

| CSV File | Purpose |
|---|---|
| dim_customer.csv | Customer dimension |
| dim_product.csv | Product dimension |
| dim_date.csv | Date dimension |
| dim_region.csv | Region dimension |
| powerbi_sales_fact.csv | Sales fact data |

### Interactive Reporting Files

| CSV File | Important Columns | Purpose |
|---|---|---|
| customer_segment_membership.csv | customer_id, customer_segment | Customer segmentation |
| return_detail.csv | return_id, customer_id, product_id, return_date, return_reason | Return-level analysis |

### Return Detail Data

The `return_detail.csv` dataset contains one row per return record.

Important fields include:

- return_id
- order_id
- customer_id
- customer_segment
- product_id
- product_name
- category
- return_date
- return_date_key
- return_year
- return_month_number
- return_year_month
- return_reason
- shipping_city
- shipping_state
- return_records

`return_records` is set to 1 for each return row and is used to count return records.

## 8. Power BI Relationships

The primary sales model uses:

| One Side | Many Side |
|---|---|
| dim_customer[customer_key] | powerbi_sales_fact[customer_key] |
| dim_product[product_key] | powerbi_sales_fact[product_key] |
| dim_date[date_key] | powerbi_sales_fact[order_date_key] |
| dim_region[region_key] | powerbi_sales_fact[region_key] |

For return reporting:

- `return_detail` contains customer segment, category and return date fields.
- `return_date_key` can be connected to `dim_date[date_key]` when their data types and date-key conventions match.
- The customer segment mapping uses `customer_id`.

Use one-to-many relationships wherever the dimension-side key is unique.

## 9. Important Metric Definitions

| Metric | Business Meaning |
|---|---|
| Gross Sales | Sales before return deductions, as defined by the project measure |
| Net Sales Before Returns | Realized sales before return deductions |
| Net Sales After Returns | Sales after return adjustments |
| Retained Profit | Profit retained after the project's return logic |
| Delivered Orders | Orders meeting the delivered-order condition |
| Return Rate | Return measure divided by its defined eligible base |
| Average Order Value | Net sales divided by the defined order count |

The precise DAX formulas in the Power BI report and SQL business logic should be treated as the source of truth for metric calculations.
