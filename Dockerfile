FROM apache/airflow:2.7.3

USER 0

RUN pip install --no-cache-dir \
    pandas>=2.2.0 \
    sqlalchemy>=2.0.23 \
    psycopg2-binary>=2.9.9 \
    python-dotenv>=1.0.0

USER 50000:0