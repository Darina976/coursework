# Дефолтный тег 2.7.3 — Python 3.8, а pandas>=2.2 требует Python >=3.9.
# pip в этом образе отказывается работать от root, поэтому ставим пакеты как airflow.
# SQLAlchemy держим <2: Airflow 2.7 на SQLAlchemy 2 не стартует.
FROM apache/airflow:2.7.3-python3.11

USER airflow

RUN pip install --no-cache-dir \
    "pandas>=2.2.0" \
    "sqlalchemy>=1.4.36,<2" \
    "psycopg2-binary>=2.9.9" \
    "python-dotenv>=1.0.0" \
    "great-expectations>=0.18.8,<0.19"