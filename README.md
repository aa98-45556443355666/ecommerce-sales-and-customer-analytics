# E-Commerce Sales & Customer Analytics Data Platform

## Overview

An end-to-end data engineering project for building an e-commerce
analytics platform using Python, PostgreSQL, Apache Airflow,
Apache Spark and Power BI.

## Business Problem

The objective is to build a scalable data platform that can ingest,
clean, transform and analyze e-commerce data related to customers,
products, orders and returns.

## Planned Architecture

The project will progressively implement:

1. Synthetic data generation
2. Data ingestion
3. Data quality validation
4. PostgreSQL staging layer
5. Data transformation
6. Star-schema data warehouse
7. Apache Airflow orchestration
8. Apache Spark analytics
9. BI dashboard
10. Testing and documentation

## Current Status

### Completed

- Project structure
- Dockerized PostgreSQL environment
- Configuration management
- Synthetic e-commerce data generator
- Sample datasets
- PostgreSQL staging schema
- Staging tables for customers, products, orders,
  order items, and returns
- Python ingestion pipeline
- Data quality  validation framework
- Duplicate, null, range, and referential-integrity checks
- Automated unit tests for validation logic
- Data cleaning and transformation
- PostgreSQL star-schema warehouse
- Warehouse integrity checks
- Business KPI SQL
- Monthly, product, customer and regional analysis
- RFM-style customer segmentation
- Return and payment-method analysis
- PySpark processing
- Airflow orchestration
- Incremental ETL and upserts
- Power BI reporting views
- Power BI CSV export pipeline

### Dashboard

The Power BI reporting layer exports curated datasets from
PostgreSQL for executive, product, customer, regional, and
return analytics.

## Apache Airflow Orchestration

The project uses Apache Airflow to orchestrate the complete
data engineering workflow.

### Pipeline Tasks

1. Ingest CSV files into PostgreSQL staging tables.
2. Run staging data quality checks.
3. Transform staging data into the clean schema.
4. Build the star-schema data warehouse.
5. Export the warehouse dataset for Spark.
6. Run PySpark analytics in a dedicated Docker container.

## Incremental ETL

The project implements file-level change detection and
idempotent upserts across staging, clean, and warehouse layers.

### Incremental Ingestion

- Calculates SHA-256 fingerprints of source CSV files.
- Stores source fingerprints and row counts in
  `etl_control.source_file_state`.
- Skips unchanged files when their fingerprint, file size,
  and staging row count match the recorded state.
- Reloads only the staging table whose source file changed.
- Updates file state and staging data in one transaction.

### Incremental Transformation

- Uses PostgreSQL upserts to insert new and update changed
  clean records.
- Avoids updates when business attributes have not changed.
- Preserves existing clean tables instead of truncating them.

### Incremental Warehouse

- Upserts customer, product, region, and date dimensions.
- Inserts new fact records and updates changed fact records.
- Validates fact counts and financial calculations.


## Automated Testing

This project includes automated tests for core data engineering
utilities and data quality validation.


## Tech Stack

- Python
- PostgreSQL
- SQL
- Apache Airflow
- Apache Spark
- Docker
- Power BI
- Git/GitHub
