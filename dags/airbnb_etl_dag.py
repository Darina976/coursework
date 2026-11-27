"""
DAG для оркестрации ETL-конвейера Airbnb (Амстердам).
Задачи: Extract -> Transform -> Quality -> Load.
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    'airbnb_etl_pipeline',
    default_args=default_args,
    description='ETL конвейер для анализа рынка краткосрочной аренды (Амстердам)',
    schedule_interval='@daily',
    start_date=datetime(2026, 11, 1),
    catchup=False,
    tags=['airbnb', 'etl', 'amsterdam'],
) as dag:

    extract_task = BashOperator(
        task_id='extract_data',
        bash_command='cd /opt/airflow && python src/extract.py',
    )

    transform_task = BashOperator(
        task_id='transform_data',
        bash_command='cd /opt/airflow && python src/transform.py',
    )

    quality_task = BashOperator(
        task_id='validate_quality',
        bash_command='cd /opt/airflow && python src/quality.py',
    )

    load_task = BashOperator(
        task_id='load_data',
        bash_command='cd /opt/airflow && python src/load.py',
    )

    extract_task >> transform_task >> quality_task >> load_task