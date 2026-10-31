
# Project Runbook

## 1. Prerequisites

Install the following:

- Git
- Python
- Docker Desktop
- Power BI Desktop (for dashboard development)

Docker Desktop should be running before starting the containerized pipeline.

## 2. Clone the Repository

```powershell
git clone https://github.com/aa98-45556443355666/ecommerce-sales-and-customer-analytics.git
cd ecommerce-sales-and-customer-analytics
```

## 3. Environment Configuration

Create a local environment file:

```powershell
Copy-Item .env.example .env
```

Configure the required database and Airflow settings in `.env`.

Do not commit `.env` or real credentials to GitHub.

The application PostgreSQL configuration uses these environment variables:

- POSTGRES_HOST
- POSTGRES_PORT
- POSTGRES_DB
- POSTGRES_USER
- POSTGRES_PASSWORD

For Docker-based application database access, the PostgreSQL host is the Compose service hostname `ecommerce_postgres`.

For local scripts running directly on the host, the host is normally `localhost`.

## 4. Install Python Dependencies

Install the project dependencies:

```powershell
python -m pip install -r requirements.txt
```

For automated testing:

```powershell
python -m pip install -r requirements-test.txt
```

## 5. Start PostgreSQL

Start the application database:

```powershell
docker compose up -d postgres
```

Verify its status:

```powershell
docker compose ps
```

The application database is separate from the Airflow metadata database.

## 6. Prepare the SQL Analytics Views

After the clean and warehouse layers have been created, execute the reporting SQL scripts in dependency order:

```powershell
Get-Content .\sql\analytics\create_powerbi_views.sql |
    docker exec -i ecommerce_postgres psql -v ON_ERROR_STOP=1 -U ecommerce -d ecommerce_db
```

```powershell
Get-Content .\sql\analytics\create_customer_segment_membership.sql |
    docker exec -i ecommerce_postgres psql -v ON_ERROR_STOP=1 -U ecommerce -d ecommerce_db
```

```powershell
Get-Content .\sql\analytics\create_return_detail_view.sql |
    docker exec -i ecommerce_postgres psql -v ON_ERROR_STOP=1 -U ecommerce -d ecommerce_db
```

These scripts depend on the relevant analytics and clean/warehouse objects already existing.

If the database is freshly created, first execute the project's staging, clean and warehouse SQL setup scripts in their documented order.

## 7. Run the Pipeline with Airflow

Start the Airflow services:

```powershell
docker compose --profile airflow up -d --build
```

On first-time initialization only:

```powershell
docker compose --profile airflow run --rm airflow-init
```

Check the Airflow metadata database:

```powershell
docker compose --profile airflow exec -T airflow-scheduler airflow db check
```

Check DAG import errors:

```powershell
docker compose --profile airflow exec -T airflow-scheduler airflow dags list-import-errors
```

List available DAGs:

```powershell
docker compose --profile airflow exec -T airflow-scheduler airflow dags list
```

Open the Airflow UI:

`http://localhost:8080`

Trigger:

`ecommerce_data_pipeline`

Expected task sequence:

1. ingest_staging
2. validate_staging
3. transform_clean
4. build_warehouse

After the warehouse load, two branches execute:

- Spark: export_spark_input → spark_analytics
- Power BI: export_powerbi_data → validate_powerbi_exports

Verify that all pipeline tasks succeed.

## 8. Power BI Data Export

The Power BI exporter can be executed manually:

```powershell
python src/analytics/export_powerbi_data.py
```

Expected output directory:

`data/processed/powerbi_output/`

Validate the exports:

```powershell
python src/analytics/validate_powerbi_exports.py
```

The validator checks required CSVs, columns, dimension keys, foreign keys and return/customer-segment consistency.

## 9. Automated Testing

Check Python syntax:

```powershell
python -m compileall -q scripts src spark airflow/dags
```

Run all unit tests:

```powershell
python -m pytest -q
```

Run only Power BI export tests:

```powershell
python -m pytest -q tests/test_powerbi_exports.py
```

## 10. Power BI Dashboard

Open Power BI Desktop.

Import the required CSV files from:

`data/processed/powerbi_output/`

Configure the relationships documented in `data_dictionary.md`.

The report contains three pages:

1. Executive Overview
2. Product & Returns
3. Customer Analytics

Create and save the Power BI Desktop report manually:

`dashboard/ecommerce_dashboard.pbix`

After a new pipeline run, refresh the report in Power BI Desktop using Home → Refresh.

CSV export does not automatically update an already-open PBIX report.

## 11. Troubleshooting

### PostgreSQL connection refused

When running inside Docker, use the PostgreSQL Compose service hostname rather than localhost.

The ingestion script reads `POSTGRES_HOST`.

### Airflow database initialization error

Check that airflow-init, airflow-scheduler and airflow-webserver all use the same Airflow metadata database.

Run:

```powershell
docker compose --profile airflow exec -T airflow-scheduler airflow db check
```

Do not use `docker compose down -v` to troubleshoot ordinary connection problems.

### DAG import errors

Run:

```powershell
docker compose --profile airflow exec -T airflow-scheduler airflow dags list-import-errors
```

Check scheduler logs:

```powershell
docker compose --profile airflow logs --tail=100 airflow-scheduler
```

### Power BI validation failure

Check whether all required CSV files were exported.

Run the exporter first, then rerun the validator.

Inspect the specific file and key reported by the validator.

## 12. Shutdown

Stop the application services:

```powershell
docker compose --profile airflow down
```

This does not request deletion of named volumes.

Do not use the `-v` option unless you intentionally want to remove persistent Docker volumes.
