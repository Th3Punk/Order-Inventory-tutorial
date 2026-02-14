#!/usr/bin/env bash
set -euo pipefail

API_URL="${API_URL:-http://localhost:18000}"
MONGO_URL="${MONGO_URL:-mongodb://mongodb:27017/app}"

echo "1) healthz"
curl -fsS "${API_URL}/healthz" >/dev/null

echo "1b) metrics"
curl -fsS "${API_URL}/metrics" >/dev/null

echo "2) register/login"
EMAIL="e2e@example.com"
PASSWORD="verylongpassword"
curl -fsS -X POST "${API_URL}/auth/register" \
  -H "content-type: application/json" \
  -d "{\"email\":\"${EMAIL}\",\"password\":\"${PASSWORD}\"}" >/dev/null || true

TOKENS="$(curl -fsS -X POST "${API_URL}/auth/login" \
  -H "content-type: application/json" \
  -d "{\"email\":\"${EMAIL}\",\"password\":\"${PASSWORD}\"}")"

ACCESS_TOKEN="$(printf "%s" "$TOKENS" | python3 - <<'PY'
import json,sys
data=json.load(sys.stdin)
print(data["access_token"])
PY
)"

echo "3) create order"
curl -fsS -X POST "${API_URL}/orders" \
  -H "content-type: application/json" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "Idempotency-Key: e2e-1" \
  -d '{"currency":"EUR","items":[{"sku":"SKU-001","qty":2,"unit_price":1000}]}' >/dev/null

echo "4) list orders"
curl -fsS "${API_URL}/orders" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" >/dev/null

echo "5) stats"
curl -fsS "${API_URL}/stats/sku" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" >/dev/null

echo "6) mongo check"
docker compose -f infra/docker-compose.yml exec -T mongodb mongosh --quiet --eval \
  "db=connect('${MONGO_URL}'); db.sku_stats.find().limit(1).toArray()" >/dev/null

echo "7) outbox published"
docker compose -f infra/docker-compose.yml exec -T db psql -U tutorial -d tutorial -c \
  "select id,event_type,created_at,published_at from outbox_events order by created_at desc limit 1;" >/dev/null

echo "8) kafka output topic"
docker compose -f infra/docker-compose.yml exec -T kafka bash -lc \
  "/usr/bin/kafka-console-consumer --bootstrap-server kafka:9092 --topic orders.sku-stats --max-messages 1 --timeout-ms 8000" >/dev/null || true

echo "9) flink job running"
docker compose -f infra/docker-compose.yml exec -T jobmanager bash -lc \
  "curl -fsS http://localhost:8081/jobs/overview | grep -q 'RUNNING'"

echo "OK"
