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

test-event:
    docker compose -f infra/docker-compose.yml exec -T kafka bash -lc "printf '%s\n' '{\"event_type\":\"OrderCreated\",\"aggregate_id\":\"debug-1\",\"payload\":{\"items\":[{\"sku\":\"SKU-001\",\"qty\":2},{\"sku\":\"SKU-002\",\"qty\":1}]},\"created_at\":\"2026-02-11T18:30:00Z\"}' | /usr/bin/kafka-console-producer --bootstrap-server kafka:9092 --topic orders.events"
