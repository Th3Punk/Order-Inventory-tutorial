# Tanuló projekt: Event‑Driven “Order & Inventory” platform (FastAPI + Kafka + Flink + Redis + Postgres + MongoDB + React/Vite + Docker Compose)

> Cél: egy **kicsi**, de **ipari jellegű** (event‑driven) rendszer felépítése **sok apró lépésben**, hogy *minden felsorolt technológia* tipikus használati eseteit megértsd.
>
> Nem „gépelési gyakorlat”: kevés funkció, de **valós minták**: auth, migráció, outbox, idempotencia, cache, stream processing, UI state management, konténerizálás, biztonság.

---

## Tartalomjegyzék

1. [Projektkoncepció és architektúra](#projektkoncepció-és-architektúra)
2. [A tanulási célok térképe](#a-tanulási-célok-térképe)
3. [Repo struktúra és alapelvek](#repo-struktúra-és-alapelvek)
4. [Docker Compose “baseline” – minden komponens konténerben](#docker-compose-baseline--minden-komponens-konténerben)
5. [Lépésről lépésre roadmap](#lépésről-lépésre-roadmap)
   - 5.1 [00 – Környezet és toolchain](#00--környezet-és-toolchain)
   - 5.2 [01 – Postgres + Alembic migrációk](#01--postgres--alembic-migrációk)
   - 5.3 [02 – FastAPI skeleton, healthcheck, strukturált logging](#02--fastapi-skeleton-healthcheck-strukturált-logging)
   - 5.4 [03 – Auth: JWT (access+refresh), password hashing, RBAC alapok](#03--auth-jwt-accessrefresh-password-hashing-rbac-alapok)
   - 5.5 [04 – CRUD (Orders) + validáció + hibakezelés](#04--crud-orders--validáció--hibakezelés)
   - 5.6 [05 – Redis: cache + rate limit + session jellegű minta](#05--redis-cache--rate-limit--session-jellegű-minta)
   - 5.7 [06 – Kafka: topicok, producer/consumer, schema‑gondolkodás](#06--kafka-topicok-producerconsumer-schemagondolkodás)
   - 5.8 [07 – Outbox pattern Postgresben (megbízható event publikálás)](#07--outbox-pattern-postgresben-megbízható-event-publikálás)
   - 5.9 [08 – Flink: stream job, aggregáció, state, checkpointing](#08--flink-stream-job-aggregáció-state-checkpointing)
   - 5.10 [09 – NoSQL: MongoDB mint “read model” / audit store](#09--nosql-mongodb-mint-read-model--audit-store)
   - 5.11 [10 – React+Vite + shadcn/ui: auth flow, forms, table](#10--reactvite--shadcnui-auth-flow-forms-table)
   - 5.12 [11 – Observability: metrics, tracing (opcionális), log korreláció](#11--observability-metrics-tracing-opcionális-log-korreláció)
   - 5.13 [12 – Biztonsági “hardening” és threat modeling mini‑gyakorlat](#12--biztonsági-hardening-és-threat-modeling-minigyakorlat)
   - 5.14 [13 – E2E ellenőrző script + “definition of done”](#13--e2e-ellenőrző-script--definition-of-done)
6. [Gyakori hibák és debug checklist](#gyakori-hibák-és-debug-checklist)
7. [Továbbfejlesztési ötletek](#továbbfejlesztési-ötletek)

---

## Projektkoncepció és architektúra

**Domain**: *Order & Inventory* (rendelések és készlet) – szándékosan egyszerű.

- A felhasználó rendelést ad le (Order).
- A rendszer **eventet** publikál (OrderCreated, OrderPaid, …).
- A **Flink** a Kafka streamből valós idejű aggregációt készít (pl. per‑termék order volume).
- A **MongoDB** egy “read model”/audit store (pl. order eventek időrendben, vagy aggregált dokumentumok).
- A **Redis** gyorsítótár és rate limit (auth endpointok védelme), valamint “hot” read cache.
- A **React/Vite + shadcn/ui** egy admin felület: login + order lista + order részletek + egyszerű dashboard.

**Mikroszerviz jelleg**, de minimalista:

- `api` – FastAPI (domain + auth + REST)
- `outbox-worker` – FastAPI repo-t használó worker, ami outbox táblából publikál Kafka‑ba
- `stream-job` – Flink job (Kafka -> aggregáció -> MongoDB)
- `web` – React/Vite UI
- infrastruktúra konténerek: Postgres, Redis, Kafka (KRaft), Flink (jobmanager/taskmanager), MongoDB

> Miért jó tanuláshoz?
> Minden komponens “tipikus”:
> - Postgres + Alembic: migráció és tranzakciók
> - FastAPI: modern async API, Pydantic v2, auth
> - Redis: cache + rate limit
> - Kafka: event streaming
> - Outbox: valós megbízhatósági minta
> - Flink: stateful stream processing
> - MongoDB: read model / audit
> - React/Vite + shadcn/ui: modern UI stack
> - Docker/Compose: lokális “mini‑prod” környezet

---

## A tanulási célok térképe

| Tech | Mit akarsz megtanulni? | Projektben hol? |
|---|---|---|
| FastAPI | routing, dependency injection, async, OpenAPI, middleware | `api` lépések |
| Alembic | migrációk, verziózás, rollback, env config | 01 |
| PostgreSQL | normalizált modell, index, tranzakció, outbox | 01, 04, 07 |
| Redis | cache-aside, TTL, rate limit, distributed lock (opcionális) | 05 |
| Kafka | topic, partition, consumer group, idempotencia, DLQ | 06, 07 |
| Flink | state, window, checkpoint, exactly-once közelítés, job deploy | 08 |
| MongoDB | dokumentum modell, upsert, read model, audit | 09 |
| React + Vite | routing, auth state, api kliens, forms | 10 |
| shadcn/ui (Vite) | modern komponensek, form patterns | 10 |
| Docker + Compose | service izoláció, env, healthcheck, network | 04… |

---

## Repo struktúra és alapelvek

Ajánlott monorepo:

```
/project-root
  /apps
    /api                # FastAPI app
    /outbox-worker       # worker (python)
    /stream-job          # Flink job (Java/Scala vagy PyFlink)
    /web                 # React/Vite + shadcn/ui
  /infra
    docker-compose.yml
    kafka/
    flink/
  /scripts
    check.sh
    seed.sh
  README.md
```

**Alapelvek:**
- **Konfiguráció 12-factor**: env varok, `.env.example`
- **Biztonság**: secret-ek lokálisan `.env`, de sose committolod
- **Idempotencia**: event feldolgozásnál, outbox publikálásnál
- **Observability**: strukturált log + request-id
- **Minimál**: csak annyi feature, ami a technológiák “mindennapi” használatához kell

---

## Docker Compose “baseline” – minden komponens konténerben

### Service lista

- `postgres` (pgsql)
- `redis`
- `kafka` (+ `kafka-ui` opcionális)
- `mongodb`
- `flink-jobmanager`, `flink-taskmanager`
- `api`
- `outbox-worker`
- `web`

### Biztonsági minimumok már lokálisan is

- Compose network izoláció (belső háló, csak szükséges port publikálás)
- Default jelszavak kerülése (pl. Postgres)
- `depends_on` + healthcheck (ne “versenyezzen” a startup)

> **Megjegyzés:** ebben a dokumentumban sok helyen adok *részleteket és snippeteket*, de célod, hogy *te írd meg* a kódot. A snippetek minták.

---

# Lépésről lépésre roadmap

## 00 – Környezet és toolchain

### Cél
Stabil fejlesztői környezet: reproducible build, lint, format, teszt keret.

### Mit és miért
- Python: 3.12+ (modern async + typing)
- Node: 20+ (Vite + modern tooling)
- Docker Desktop / Docker Engine
- `uv` vagy `poetry` (Python dependency management) – modern és gyors; tanuláshoz `uv` egyszerű
- `ruff` + `mypy` + `pytest`
- Frontend: `pnpm` (gyors, determinisztikus)

### Feladatok
1. Hozd létre a monorepo mappákat (`apps`, `infra`, `scripts`).
2. Python oldalon:
   - init `apps/api` és `apps/outbox-worker` külön projectként
   - rögzített dependency verziók (lock)
3. Frontend:
   - `apps/web` Vite React TS template
4. Adj hozzá:
   - `pre-commit` hook (ruff, prettier, eslint)
   - `make` vagy `just` parancsok (opcionális)

### Ellenőrzés
- `docker --version`
- `python --version`, `node --version`
- `ruff --version`, `pytest --version`
- `pnpm --version`

---

## 01 – Postgres + Alembic migrációk

### Cél
Adatbázis feláll Dockerben, első sémák migrációval, rollback kipróbálása.

### Mit használj
- PostgreSQL 16+
- SQLAlchemy 2.x (ajánlott async engine)
- Alembic (migráció)
- `psql` vagy admin tool (pl. DBeaver)

### Modellek (minimál)
- `users`: id, email (unique), password_hash, role, created_at
- `orders`: id, user_id (FK), status, total_amount, created_at
- `outbox_events`: id, aggregate_type, aggregate_id, event_type, payload_json, created_at, published_at (nullable)

**Miért outbox tábla már itt?**
- Később a Kafka publikálást a DB tranzakcióval együtt akarod “egészben” kezelni.

### Fontos DB tanulási pontok
- indexek: `users(email)`, `orders(user_id, created_at)`
- FK és CASCADE / RESTRICT döntések
- timestampek: `timestamptz` használata

### Példa: Alembic workflow (parancsok)
```bash
# api app könyvtárában (vagy monorepo rootból make/just)
alembic init alembic
alembic revision -m "init schema" --autogenerate
alembic upgrade head

# rollback gyakorlat
alembic downgrade -1
alembic upgrade head
```

### Ellenőrzés
```bash
docker compose -f infra/docker-compose.yml up -d postgres
psql "$DATABASE_URL" -c "\dt"
psql "$DATABASE_URL" -c "select * from users limit 1;"
```

---

## 02 – FastAPI skeleton, healthcheck, strukturált logging

### Cél
Fut egy minimál FastAPI, van `/healthz`, van OpenAPI, van request-id és JSON log.

### Mit és miért
- FastAPI (latest)
- Pydantic v2
- Uvicorn
- Strukturált logging: `structlog` vagy Python stdlib + JSON formatter
- Middleware: request-id (korreláció), security headers

### Feladatok
1. App factory pattern (`create_app()`).
2. `settings` modul (Pydantic Settings): env varok.
3. Health endpoint:
   - DB ping (SELECT 1)
   - Redis ping (később)
4. CORS beállítás (csak dev origin)
5. Security headers middleware (legalább: `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`)

### Ellenőrzés
```bash
curl -s http://localhost:8000/healthz | jq .
curl -s http://localhost:8000/openapi.json | jq '.info'
```

---

## 03 – Auth: JWT (access+refresh), password hashing, RBAC alapok

### Cél
Biztonságos authentikáció:
- regisztráció + login
- access token (rövid életű) + refresh token (hosszabb)
- password hashing (Argon2 vagy bcrypt)
- alap role (pl. `user`, `admin`)

### Mit használj
- `passlib` + `argon2-cffi` (argon2 ajánlott)
- JWT: `python-jose` vagy `PyJWT`
- FastAPI security: OAuth2PasswordBearer (password flow)
- Refresh token tárolás: Postgres (hashed) vagy Redis (revocation list) – tanulási célból Postgres

### Biztonsági elvek (tanuld és alkalmazd)
- **Soha** nem tárolsz plain text jelszót.
- JWT secret: env var, elég hosszú, rotációra felkészülni.
- Refresh token “one-time use” jelleg: új login/refresh új tokeneket ad, régit érvényteleníti.
- Rate limit loginon (Redis lépésnél erősítjük).
- Hibák: ne szivárogjon, hogy email létezik-e.

### Minimál endpointok
- `POST /auth/register`
- `POST /auth/login` (token pair)
- `POST /auth/refresh`
- `POST /auth/logout` (refresh token revoke)

### Példa: password hash ellenőrzés (snippet)
```python
from passlib.context import CryptContext
pwd = CryptContext(schemes=["argon2"], deprecated="auto")

def hash_password(p: str) -> str:
    return pwd.hash(p)

def verify_password(p: str, h: str) -> bool:
    return pwd.verify(p, h)
```

### Ellenőrzés (curl script)
```bash
# register
curl -s -X POST http://localhost:8000/auth/register   -H 'content-type: application/json'   -d '{"email":"u1@example.com","password":"S3cure!passw0rd"}' | jq .

# login
TOKENS=$(curl -s -X POST http://localhost:8000/auth/login   -H 'content-type: application/json'   -d '{"email":"u1@example.com","password":"S3cure!passw0rd"}')

echo "$TOKENS" | jq .
ACCESS=$(echo "$TOKENS" | jq -r .access_token)
curl -s http://localhost:8000/me -H "authorization: Bearer $ACCESS" | jq .
```

---

## 04 – CRUD (Orders) + validáció + hibakezelés

### Cél
Egy kicsi domain endpoint készlet:
- order létrehozás
- lista saját orderjeidről
- admin listázás
- státusz váltás (pl. `created -> paid`)

### Mit és miért
- Pydantic v2 modellek (request/response)
- SQLAlchemy ORM (async)
- Repository/service réteg (tanulási célból)
- Hibakezelés:
  - 400 validáció
  - 401/403 auth
  - 404 hiány
  - 409 konfliktus (idempotencia)

### Tanulási pontok
- Input validáció (pl. összeg > 0)
- Authorization check (user csak a saját orderjeit)
- DB tranzakció: order + outbox event **egy** tranzakcióban (előfutár a 07‑hez)

### Ellenőrzés
- `POST /orders`
- `GET /orders`
- admin tokennel `GET /admin/orders`
- `PATCH /orders/{id}/status`

Készíts `scripts/seed.sh`-t, ami:
1) regisztrál 2 usert (user+admin),
2) beléptet,
3) létrehoz 3 ordert.

---

## 05 – Redis: cache + rate limit + session jellegű minta

### Cél
Redis integráció 3 tipikus esetre:
1) cache-aside read cache (order részletek)
2) rate limit (login endpoint)
3) token revoke/denylist (opcionális)

### Mit és miért
- `redis-py` (async)
- Cache-aside:
  - DB az igazság forrása
  - Redis TTL (pl. 60s), invalidate updatekor
- Rate limit:
  - leaky bucket vagy fixed window (tanulási célból fixed window ok)
  - kulcs: `rl:login:{ip}`

### Példa: fix window rate limit (snippet)
```python
# Pseudo
key = f"rl:login:{ip}:{current_minute}"
count = await redis.incr(key)
if count == 1:
    await redis.expire(key, 60)
if count > 10:
    raise HTTPException(429, "Too many requests")
```

### Ellenőrzés
```bash
# redis ping
docker exec -it redis redis-cli PING

# rate limit teszt (11 gyors próbálkozás)
for i in $(seq 1 11); do
  curl -s -o /dev/null -w "%{http_code}
"     -X POST http://localhost:8000/auth/login     -H 'content-type: application/json'     -d '{"email":"u1@example.com","password":"bad"}'
done
```

---

## 06 – Kafka: topicok, producer/consumer, schema‑gondolkodás

### Cél
Kafka alapok, eventek publikálása és fogyasztása lokálisan.

### Mit és miért
- Kafka KRaft módban (Zookeeper nélkül) Compose-ban
- `kcat` (korábban kafkacat) debughoz
- Python oldalon: `confluent-kafka` (gyors, librdkafka), vagy `aiokafka` (oktatásra)
- Topicok:
  - `orders.events` (OrderCreated/OrderPaid)
  - `orders.dlq` (dead-letter queue, ha consumer nem tud feldolgozni)

### Tanulási pontok
- Key használat: `order_id` (partitioning)
- Consumer group
- At-least-once feldolgozás és idempotencia (később)
- Schema: kezdd JSON-nal, de gondolkodj verziózásban (field add, backward compat)

### Ellenőrzés
```bash
# topic list
docker exec -it kafka kafka-topics.sh --bootstrap-server localhost:9092 --list

# consume
docker run --rm --network=infra_default edenhill/kcat:1.7.1   -b kafka:9092 -t orders.events -C -o beginning -q
```

---

## 07 – Outbox pattern Postgresben (megbízható event publikálás)

### Cél
Megbízható event publikálás DB tranzakcióval együtt:
- amikor order létrejön, outbox táblába kerül event
- külön worker publikálja Kafka‑ba
- siker esetén `published_at` kitöltése

### Miért fontos
Ez *valós* ipari minta, hogy elkerüld:
- “DB commit megtörtént, de Kafka publish elbukott”
- “Kafka publish megvolt, de DB rollbackelt”

### Megvalósítási lépések
1. `POST /orders` tranzakcióban:
   - insert order
   - insert outbox_events (payload: JSON)
2. `outbox-worker`:
   - poll: `select ... where published_at is null order by created_at limit N for update skip locked`
   - publish to Kafka
   - update published_at
3. Idempotencia:
   - Kafka producer enable idempotence (ha librdkafka)
   - publish után commit logika (ha publish fail, ne update-eld)

### Ellenőrzés
- hozz létre ordert
- nézd meg Postgresben az outbox sort
- nézd meg Kafka-ban, hogy megjelent az event

```bash
psql "$DATABASE_URL" -c "select id,event_type,created_at,published_at from outbox_events order by created_at desc limit 5;"
```

---

## 08 – Flink: stream job, aggregáció, state, checkpointing

### Cél
Egy valós idejű stream feldolgozó:
- input: `orders.events`
- feldolgozás: per‑product/per‑minute aggregáció (vagy per státusz)
- output: MongoDB upsert (read model) *vagy* külön Kafka topic

### Ajánlott egyszerű feladat
- Event payload tartalmazzon `items: [{sku, qty, price}]`
- Flink számolja sku-nként az össz mennyiséget 1 perces tumbling window-val

### Mit és miért
- Flink (JobManager + TaskManager konténer)
- Checkpointing bekapcsolása (legalább tanulásra)
- State backend (RocksDB opcionális, de lokálisan egyszerű in-memory)
- Kafka connector
- Mongo sink (ha nincs kényelmes connector, akkor: output Kafka + külön consumer ír MongoDB-be – tanulásra ez is jó)

### Ellenőrzés
- Flink UI: `http://localhost:8081`
- Adj le rendelést
- Nézd meg, hogy nő az aggregált érték MongoDB-ben vagy output topicban

---

## 09 – NoSQL: MongoDB mint “read model” / audit store

### Cél
MongoDB használata két tipikus módon:
1) Audit/event store jelleg: order eventek append-only
2) Read model: aggregált dokumentumok (sku_stats)

### Mit és miért
- MongoDB (konténer)
- Gyors dokumentum lekérdezés UI-hoz
- Upsert pattern

### Példa dokumentum
`sku_stats`:
```json
{
  "sku": "ABC-123",
  "window_start": "2026-01-31T10:00:00Z",
  "window_end": "2026-01-31T10:01:00Z",
  "qty_sum": 42,
  "updated_at": "..."
}
```

### Ellenőrzés
```bash
docker exec -it mongodb mongosh --eval 'db.getMongo().getDBNames()'
docker exec -it mongodb mongosh --eval 'db=connect("mongodb://localhost:27017/app"); db.sku_stats.find().limit(5).toArray()'
```

---

## 10 – React+Vite + shadcn/ui: auth flow, forms, table

### Cél
Modern frontend:
- login oldal
- order lista + részletek
- egyszerű “stats” nézet (Mongo read model)

### Modern stack javaslat (tanuláshoz erős)
- React 18 + Vite + TypeScript
- React Router
- TanStack Query (server state)
- `zod` + `react-hook-form` (form validáció)
- shadcn/ui + Tailwind
- `ky` vagy `axios` kliens (tanulásra bármelyik jó)

### Feladatok
1. shadcn/ui telepítés Vite-hoz (kövesd az aktuális shadcn docsot; Vite támogatott).
2. Layout:
   - App shell (navbar)
   - Protected routes (csak ha van access token)
3. Auth state:
   - token tárolás: memóriában + refresh cookie (ajánlott) **vagy** localStorage (dev)
   - tanulási cél: értsd XSS kockázatokat; preferáld httpOnly cookie refresh tokenhez
4. Order lista:
   - table komponens (shadcn DataTable minta)
5. Forms:
   - create order (pár mező)
6. Error handling:
   - 401 esetén refresh flow
   - toast/alert (shadcn)

### Ellenőrzés
- `pnpm dev` és be tudsz lépni
- létrehozol ordert UI-ból
- listában megjelenik

---

## 11 – Observability: metrics, tracing (opcionális), log korreláció

### Cél
Lásd, mi történik:
- API request logok request-id-val
- basic metrics endpoint (prometheus kompatibilis)
- Kafka consumer lag szemléltetés (kafka-ui)

### Mit és miért
- `prometheus-fastapi-instrumentator` (egyszerű)
- Kafka UI konténer (pl. provectuslabs/kafka-ui)
- Flink UI alapból

### Ellenőrzés
- `GET /metrics`
- Kafka UI-ban látod a topicokat/consumer groupot
- Flink UI-ban fut a job

---

## 12 – Biztonsági “hardening” és threat modeling mini‑gyakorlat

### Cél
Ne csak “működjön”, hanem legyen **védhető**.

### Gyakorlat (konkrét)
1. Készíts egy mini threat modelt:
   - assets: user account, order data, tokens
   - entry points: login, create order, kafka consumer
   - fenyegetések: brute force, token theft (XSS), SQLi, SSRF, deserialization, insecure deps
2. Implementáld a minimum védelmeket:
   - password policy (min length + “not common” jelleg)
   - rate limit loginra
   - CORS szigor
   - secure headers
   - input validáció mindenhol
   - SQLAlchemy param binding (ORM alapból)
   - dependency pinning + `pip-audit` / `npm audit` (tanulás)
3. Secret kezelés:
   - `.env` csak lokálisan
   - compose secrets (opcionális)
4. Kafka:
   - tanuld meg: auth/TLS productionban kell; lokálisan plain ok, de dokumentáld.

### Ellenőrzés
- próbálj brute force scriptet -> 429
- próbálj nem jogosult ordert lekérni -> 403
- próbálj hibás payloadot -> 422

---

## 13 – E2E ellenőrző script + “definition of done”

### Cél
Egy gombnyomásra tudod ellenőrizni, hogy “minden drót össze van kötve”.

### `scripts/check.sh` (ötlet)
A script ellenőriz:
- compose fut
- healthz ok
- login ok
- create order -> outbox -> kafka -> flink -> mongo
- redis cache key létrejön (order details után)

### Példa ellenőrző lépések (pszeudo)
```bash
# 1) health
curl -sf http://localhost:8000/healthz

# 2) register+login
# 3) create order
# 4) kafka consume vár 5 mp-ig, hogy megjelenik-e event
# 5) mongo query: sku_stats nőtt-e
```

### Definition of Done (DoD)
- `docker compose up -d` után 1 percen belül minden green (healthcheck)
- `scripts/seed.sh` és `scripts/check.sh` sikeres
- OpenAPI dokumentáció elérhető
- Alap security védelmek működnek

---

## Gyakori hibák és debug checklist

### Postgres/Alembic
- Alembic autogenerate nem lát modelleket → `target_metadata` nincs bekötve
- Async engine + Alembic: külön figyelni a `env.py`-re

### Kafka
- rossz listener/advertised listener → hostról nem éred el
- consumer group “nem lát semmit” → offset enden van, használd `-o beginning`

### Redis
- TTL hiány → memória nő
- cache invalidáció elmarad → stale adat

### Flink
- connector verzió inkompatibilitás → válassz kompatibilis Flink+Kafka connector párost
- checkpoint path nem írható → volume/permission

### Frontend auth
- 401 loop → refresh flow rossz
- CORS + cookie → `credentials: include` kell

---

## Továbbfejlesztési ötletek

- Email verification / MFA (TOTP)
- CQRS: külön read API
- Kafka schema registry + Avro/Protobuf
- Flink exactly-once end-to-end (később)
- OpenTelemetry tracing (Jaeger)
- Kubernetes (minikube/k3d) deploy

---

# Mellékletek

## Ajánlott Docker Compose elemek (irányelvek)

- Minden service kapjon:
  - `healthcheck`
  - saját volume (ha stateful)
  - “belső” network
- API/web portok publikálása hostra, a többi csak internal.

## Ajánlott env változók (minta)

- `DATABASE_URL=postgresql+asyncpg://...`
- `REDIS_URL=redis://redis:6379/0`
- `KAFKA_BOOTSTRAP_SERVERS=kafka:9092`
- `JWT_SECRET=...`
- `JWT_ACCESS_TTL_SECONDS=900`
- `JWT_REFRESH_TTL_SECONDS=1209600`
- `MONGO_URL=mongodb://mongodb:27017/app`

---

## Hogyan használd ezt a dokumentumot

1. Menj lépésről lépésre, és **minden lépés után állj meg**.
2. A “Cél” és “Ellenőrzés” részek alapján validáld, hogy kész vagy.
3. Csak akkor lépj tovább, ha:
   - érted, miért így csináltad
   - tudod reprodukálni
   - tudod debugolni, ha elromlik

---

*Vége.*
