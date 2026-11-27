# Запуск

Нужны Docker Desktop и Docker Compose. Перед командами откройте Docker Desktop и дождитесь, пока демон запустится.

## 1. Переменные окружения

В корне проекта создайте файл `.env`. Без него Postgres не стартует, а Airflow ждёт healthy Postgres и тоже не поднимается.

```env
POSTGRES_USER=airbnb_user
POSTGRES_PASSWORD=airbnb_secure_pass
POSTGRES_DB=airbnb_dwh
POSTGRES_HOST=postgres
POSTGRES_PORT=5432

AIRFLOW_ADMIN_USER=admin
AIRFLOW_ADMIN_PASSWORD=admin
```

`POSTGRES_USER`, `POSTGRES_PASSWORD` и `POSTGRES_DB` должны совпадать с этими значениями: их же использует загрузка в `src/load.py`.

## 2. Сборка и запуск

Из корня проекта:

```bash
docker compose up -d --build
```

Первый запуск скачивает образы и собирает `my-airflow`, это занимает несколько минут. Проверка:

```bash
docker compose ps
```

Ожидаемое состояние:

| Сервис | Статус |
|---|---|
| postgres | `healthy` |
| airflow-init | `Exited (0)` |
| airflow-webserver | `Up` |
| airflow-scheduler | `Up` |
| grafana | `Up` |

`airflow-init` останавливается после создания схемы и пользователя. Код 0 — нормальное завершение, контейнер не должен оставаться запущенным.

## 3. Интерфейсы

| Сервис | Адрес | Логин | Пароль |
|---|---|---|---|
| Airflow | http://localhost:8080 | `admin` | `admin` |
| Grafana | http://localhost:3000 | `admin` | `admin` |
| PostgreSQL | `localhost:5432` | `airbnb_user` | `airbnb_secure_pass` |

База: `airbnb_dwh`. В Airflow DAG называется `airbnb_etl_pipeline`.

## Остановка

```bash
docker compose down
```

Данные Postgres и Grafana остаются в томах. Чтобы удалить их вместе с контейнерами:

```bash
docker compose down -v
```
