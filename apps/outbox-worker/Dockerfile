FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml /app/pyproject.toml

RUN uv sync

COPY app /app/app

CMD ["uv", "run", "outbox-worker"]
