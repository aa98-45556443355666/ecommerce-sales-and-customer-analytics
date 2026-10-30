from __future__ import annotations

import logging
import os
import subprocess
import sys

from datetime import datetime, timedelta
from pathlib import Path

from airflow import DAG
from airflow.providers.docker.operators.docker import DockerOperator
from airflow.operators.python import PythonOperator
from docker.types import Mount


logger = logging.getLogger(__name__)

PROJECT_DIR = Path(
    os.environ.get(
        "PROJECT_DIR",
        "/opt/airflow/project",
    )
).resolve()


# ---------------------------------------------------------
# RUN EXISTING PROJECT SCRIPTS
# ---------------------------------------------------------

def run_project_script(script_relative_path: str) -> None:
    """
    Run a project Python script inside the Airflow scheduler container.
    Raise an exception if the script is missing or fails.
    """
    project_root = Path(
        os.environ.get(
            "ECOMMERCE_PROJECT_ROOT",
            "/opt/airflow/project",
        )
    ).resolve()

    script_path = (project_root / script_relative_path).resolve()

    # Prevent accidental execution of paths outside the project.
    if not script_path.is_relative_to(project_root):
        raise ValueError(
            f"Script path is outside project root: {script_path}"
        )

    if not project_root.is_dir():
        raise FileNotFoundError(
            f"Project directory not found: {project_root}"
        )

    if not script_path.is_file():
        raise FileNotFoundError(
            f"Project script not found: {script_path}"
        )

    env = os.environ.copy()

    # Use the PostgreSQL service name from Docker Compose.
    # Use the PostgreSQL service name from Docker Compose.
# load_data.py reads POSTGRES_HOST, not DB_HOST.
    env["POSTGRES_HOST"] = os.environ.get(
        "POWERBI_DB_HOST",
        "ecommerce_postgres",
    )

    print(f"Running project script: {script_path}")

    subprocess.run(
        [sys.executable, str(script_path)],
        cwd=str(project_root),
        env=env,
        check=True,
    )


def export_powerbi_data() -> None:
    """Generate the reporting CSV files for Power BI."""
    run_project_script(
        "src/analytics/export_powerbi_data.py"
    )


def validate_powerbi_exports() -> None:
    """Validate all required Power BI reporting CSVs."""
    run_project_script(
        "src/analytics/validate_powerbi_exports.py"
    )

# ---------------------------------------------------------
# DAG DEFINITION
# ---------------------------------------------------------


default_args = {
    "owner": "data-engineering",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=2),
}


with DAG(
    dag_id="ecommerce_data_pipeline",
    description=(
        "End-to-end e-commerce ingestion, quality, "
        "transformation, warehouse and Spark analytics."
    ),

    # Manual trigger until incremental source ingestion
    # is implemented.
    schedule=None,

    start_date=datetime(2026, 1, 1),
    catchup=False,
    max_active_runs=1,

    default_args=default_args,

    tags=[
        "ecommerce",
        "data-engineering",
        "postgresql",
        "pyspark",
    ],

) as dag:

    # -----------------------------------------------------
    # TASK 1: INGESTION
    # -----------------------------------------------------

    ingest_staging = PythonOperator(
        task_id="ingest_staging",
        python_callable=run_project_script,
        op_kwargs={
            "script_relative_path":
                "src/ingestion/load_data.py"
        },
    )

    # -----------------------------------------------------
    # TASK 2: DATA QUALITY
    # -----------------------------------------------------

    validate_staging = PythonOperator(
        task_id="validate_staging",
        python_callable=run_project_script,
        op_kwargs={
            "script_relative_path":
                "src/validation/validate_data.py"
        },
    )

    # -----------------------------------------------------
    # TASK 3: CLEANING AND TRANSFORMATION
    # -----------------------------------------------------

    transform_clean = PythonOperator(
        task_id="transform_clean",
        python_callable=run_project_script,
        op_kwargs={
            "script_relative_path":
            "src/transformation/incremental_transform_data.py"
        },
    )

    # -----------------------------------------------------
    # TASK 4: DATA WAREHOUSE
    # -----------------------------------------------------

    build_warehouse = PythonOperator(
        task_id="build_warehouse",
        python_callable=run_project_script,
        op_kwargs={
            "script_relative_path":
            "src/warehouse/load_incremental_warehouse.py"
        },
    )

    # -----------------------------------------------------
    # TASK 5: EXPORT INPUT FOR SPARK
    # -----------------------------------------------------

    export_spark_input = PythonOperator(
        task_id="export_spark_input",
        python_callable=run_project_script,
        op_kwargs={
            "script_relative_path":
                "src/spark/export_spark_input.py"
        },
    )

    # -----------------------------------------------------
    # TASK 6: RUN PYSPARK INSIDE A DOCKER CONTAINER
    # -----------------------------------------------------

    spark_analytics = DockerOperator(
        task_id="spark_analytics",

        image="ecommerce-spark-runner:latest",

        command=[
            "/app/spark/sales_aggregation.py"
        ],

        docker_url="unix://var/run/docker.sock",
        api_version="auto",

        # Same named Docker volume used by the exporter.
        mounts=[
            Mount(
                source="ecommerce_processed_data",
                target="/app/data/processed",
                type="volume",
            )
        ],

        environment={
            "PYSPARK_PYTHON": "python3",
            "PYSPARK_DRIVER_PYTHON": "python3",
        },

        # Match the shared volume's permission setup.
        # The official Spark image's spark UID is 185.
        user="185:0",

        mount_tmp_dir=False,
        auto_remove="success",
        force_pull=False,

        mem_limit="2g",
        execution_timeout=timedelta(hours=1),
    )

    powerbi_export_task = PythonOperator(
        task_id="export_powerbi_data",
        python_callable=export_powerbi_data,
    )

    powerbi_validation_task = PythonOperator(
        task_id="validate_powerbi_exports",
        python_callable=validate_powerbi_exports,
    )

    # -----------------------------------------------------
    # TASK DEPENDENCIES
    # -----------------------------------------------------

    # Main ETL pipeline
    (
        ingest_staging
        >> validate_staging
        >> transform_clean
        >> build_warehouse
    )

    # Branch 1: Spark analytics
    (
        build_warehouse
        >> export_spark_input
        >> spark_analytics
    )

    # Branch 2: Power BI reporting
    (
        build_warehouse
        >> powerbi_export_task
        >> powerbi_validation_task
    )
