lint:
    ruff check apps/api

format:
    ruff format apps/api

api-add pkg:
    uv add --project apps/api {{pkg}}

compose:
    docker-compose -f infra/docker-compose.yml up -d --build

compose-containers containers:
    docker-compose -f infra/docker-compose.yml up -d --build {{containers}}
