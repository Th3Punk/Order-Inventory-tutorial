lint:
    ruff check apps/api

format:
    ruff format apps/api

api-add pkg:
    uv add --project apps/api {{pkg}}

worker-add pkg:
    uv add --project apps/outbox-worker {{pkg}}

flink-add pkg:
    uv add --project apps/stream-job {{pkg}}

compose:
    docker-compose -f infra/docker-compose.yml up -d --build

compose-containers containers:
    docker-compose -f infra/docker-compose.yml up -d --build {{containers}}

alembic-revision message:
    PYTHONPATH=apps/api alembic -c apps/api/alembic.ini revision -m "{{message}}" --autogenerate

migrate:
  docker compose -f infra/docker-compose.yml run --rm api alembic upgrade head
