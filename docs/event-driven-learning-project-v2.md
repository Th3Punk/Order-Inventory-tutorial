# Tanuló projekt: Event-Driven “Order & Inventory” platform  
**FastAPI + Kafka + Flink + Redis + PostgreSQL + MongoDB + React/Vite + shadcn/ui + Docker Compose**

> **Cél:** egy kicsi, de ipari jellegű (event-driven) rendszer felépítése **sok apró lépésben**, úgy, hogy közben megértsd a felsorolt komponensek **gyakori használati eseteit** és a **biztonságos implementáció** alapelveit.  
> **Nem kész kód**: a dokumentum specifikációt, döntéseket, ellenőrzési pontokat és minimál snippeteket ad. A kódot te írod.

---

## Tartalomjegyzék

1. [Projektkoncepció és célok](#projektkoncepció-és-célok)  
2. [Architektúra és adatfolyam](#architektúra-és-adatfolyam)  
3. [Végpontok, események, read model – specifikáció](#végpontok-események-read-model--specifikáció)  
4. [Repo struktúra és konvenciók](#repo-struktúra-és-konvenciók)  
5. [Docker Compose baseline](#docker-compose-baseline)  
6. [Roadmap lépésről lépésre](#roadmap-lépésről-lépésre)  
   - [00 – Toolchain, minőségkapuk](#00--toolchain-minőségkapuk)  
   - [01 – PostgreSQL + Alembic + DB sémák](#01--postgresql--alembic--db-sémák)  
   - [02 – FastAPI skeleton + config + logging](#02--fastapi-skeleton--config--logging)  
   - [03 – Auth: JWT access+refresh, RBAC](#03--auth-jwt-accessrefresh-rbac)  
   - [04 – Orders API: CRUD + idempotencia + outbox írás](#04--orders-api-crud--idempotencia--outbox-írás)  
   - [05 – Redis: cache-aside + rate limit + token revoke minta](#05--redis-cache-aside--rate-limit--token-revoke-minta)  
   - [06 – Kafka: topicok, producer/consumer, DLQ](#06--kafka-topicok-producerconsumer-dlq)  
   - [07 – Outbox worker: poll, publish, retry](#07--outbox-worker-poll-publish-retry)  
   - [08 – Flink: stream feldolgozás + window + state + checkpoint](#08--flink-stream-feldolgozás--window--state--checkpoint)  
   - [09 – MongoDB: audit + read model + upsert](#09--mongodb-audit--read-model--upsert)  
   - [10 – React/Vite + shadcn/ui: auth flow + táblák + űrlapok](#10--reactvite--shadcnui-auth-flow--táblák--űrlapok)  
   - [11 – Observability: metrics + UI-k](#11--observability-metrics--ui-k)  
   - [12 – Security hardening + threat modeling](#12--security-hardening--threat-modeling)  
   - [13 – E2E ellenőrzés: seed + check script](#13--e2e-ellenőrzés-seed--check-script)  
7. [Gyakori hibák / debug checklist](#gyakori-hibák--debug-checklist)  
8. [Továbbfejlesztések](#továbbfejlesztések)  

---

## Projektkoncepció és célok

**Domain**: egyszerű *Order & Inventory*.

- A felhasználó rendelést ad le (Order).
- A rendszer megbízhatóan publikál eseményeket Kafka-ba (Outbox pattern).
- A Flink valós idejű aggregációkat készít (pl. SKU-ként mennyiség percenként).
- A MongoDB read model (dashboardhoz) és audit store (esemény napló).
- Redis cache és rate limit (biztonság, teljesítmény).

**Kisebb funkciók, de valós minták:**
- Access+refresh JWT, revoke, rate limit
- Validáció és jogosultságok
- Idempotens API (idempotency-key)
- Outbox -> Kafka megbízhatóság
- Stream feldolgozás (window, state, checkpoint)
- UI auth flow + server state (TanStack Query)
- Docker Compose “mini-prod” környezet

---

## Architektúra és adatfolyam

### Szolgáltatások
- `api` – FastAPI: auth + orders REST
- `outbox-worker` – Python worker: outbox táblából publish Kafka
- `stream-job` – Flink job: Kafka -> aggregáció -> MongoDB (vagy Kafka output)
- `web` – React/Vite admin UI

### Infrastruktúra
- Postgres, Redis, Kafka (KRaft), MongoDB
- Flink JobManager + TaskManager
- Kafka UI (opcionális, nagyon hasznos tanuláshoz)

### Data flow (rövid)
1. `POST /orders` -> Postgres `orders` + `outbox_events` (egy tranzakció)
2. `outbox-worker` -> publish `orders.events` topicba
3. `stream-job` Flink -> aggregate -> MongoDB `sku_stats`
4. `web` -> REST API (`orders`) + read model endpoint (`/stats/sku`)

---

## Végpontok, események, read model – specifikáció

Ez a fejezet “single source of truth” a projekt implementációjához.

### 1) Auth API

#### `POST /auth/register`
**Request JSON**
```json
{
  "email": "user@example.com",
  "password": "S3cure!passw0rd",
  "role": "user"
}
```
**Validáció**
- `email`: kötelező, RFC-szerű formátum (Pydantic EmailStr).
- `password`:
  - min 12 karakter
  - tartalmazzon legalább 1 kisbetűt, 1 nagybetűt, 1 számot, 1 speciális karaktert
  - tiltott/common jelszó lista (legalább 50–100 gyakori jelszó) – tanulási célból elég egy kis lista is
- `role`: csak `user` vagy `admin`. **Biztonság:** normál regisztrációnál **ne engedd adminra** – vagy csak egy “bootstrap env var” alapján.

**Response (201)**
```json
{
  "id": "uuid",
  "email": "user@example.com",
  "role": "user",
  "created_at": "ISO8601"
}
```
**Hibák**
- 409: email már létezik (ne áruld el túl részletesen)
- 422: validáció

#### `POST /auth/login`
**Request JSON**
```json
{ "email": "user@example.com", "password": "..." }
```
**Validáció / védelem**
- Rate limit: IP alapon (Redis, később)
- Nem adsz eltérő üzenetet “email nincs” vs “jelszó rossz”

**Response (200)**
```json
{
  "access_token": "jwt",
  "access_expires_in": 900,
  "refresh_token": "jwt_or_random",
  "refresh_expires_in": 1209600
}
```

**Token ajánlás**
- Access token: JWT, TTL 15 perc
- Refresh token: **random** (opaque) token ajánlott, DB-ben hashed, és a kliensnek cookieban (httpOnly) – UI-hoz tanulságos.

#### `POST /auth/refresh`
**Request**
- Ha cookie: üres body, refresh token cookieból
- Ha JSON: `{ "refresh_token": "..." }` (dev egyszerűség)

**Response (200)**: új token pair  
**Validáció**
- refresh token létezik, nem revoked, nem expired
- one-time use: refresh siker után régi refresh érvénytelenít

#### `POST /auth/logout`
- refresh token revoke

#### `GET /me`
- bearer access token
- response: user profil

---

### 2) Orders API

#### Order modell (API)
- `id`: uuid
- `user_id`: uuid
- `status`: `created | paid | canceled`
- `currency`: `HUF | EUR | USD` (tanulási célból fix enum)
- `total_amount`: integer (minor units, pl. HUF fillér helyett forint – döntsd el)
- `items`: lista (sku, qty, unit_price)
- `created_at`

#### `POST /orders`
**Kötelező: idempotencia**
- Header: `Idempotency-Key: <uuid>`  
- Tárolás: Postgres tábla `idempotency_keys` (user_id + key unique) vagy orders táblában mező.

**Request JSON**
```json
{
  "currency": "HUF",
  "items": [
    { "sku": "SKU-001", "qty": 2, "unit_price": 1590 },
    { "sku": "SKU-ABC", "qty": 1, "unit_price": 7990 }
  ]
}
```

**Validáció**
- `items`:
  - min 1 elem, max 50
  - `sku`: 3..64 chars, `[A-Z0-9-_]` (regex)
  - `qty`: 1..1000
  - `unit_price`: 0..10_000_000
- `currency`: enum
- `total_amount` szerver oldalon számolódik: `sum(qty * unit_price)`
- Overflow ellenőrzés (int tartomány)
- Idempotency-Key:
  - hiány: 400 (tanulási cél)
  - rossz formátum: 422 vagy 400

**Response (201)**
```json
{
  "id": "uuid",
  "status": "created",
  "currency": "HUF",
  "total_amount": 11170,
  "items": [
    { "sku": "SKU-001", "qty": 2, "unit_price": 1590, "line_total": 3180 },
    { "sku": "SKU-ABC", "qty": 1, "unit_price": 7990, "line_total": 7990 }
  ],
  "created_at": "ISO8601"
}
```

**Hibák**
- 401: no token
- 409: ugyanazzal az idempotency key-jel más payload (konfliktus)
- 422: validáció

**Oldalhatás**
- DB tranzakcióban: order + outbox_event (`OrderCreated`)

#### `GET /orders`
- query paramok:
  - `limit` (default 20, max 100)
  - `cursor` (created_at+id alapú cursor)
  - `status` (optional)

**Validáció**
- limit tartomány
- cursor formátum

**Response (200)**
```json
{
  "items": [ { "id": "...", "status": "...", "total_amount": 123, "created_at": "..." } ],
  "next_cursor": "opaque_or_null"
}
```

#### `GET /orders/{order_id}`
- user csak a sajátját
- cache-aside (Redis): `order:{id}` TTL 60s

#### `PATCH /orders/{order_id}/status`
- body:
```json
{ "status": "paid" }
```
**Szabályok**
- `created -> paid` ok
- `created -> canceled` ok
- `paid -> canceled` tiltott (409)
- státusz váltás outbox eventet generál (`OrderPaid`, `OrderCanceled`)

**Response (200)**: order snapshot

#### Admin
- `GET /admin/orders` (RBAC: admin)
- query: `user_id`, `status`, `limit`, `cursor`

---

### 3) Kafka események

Topic: `orders.events`  
Key: `order_id` (uuid string)

#### Event envelope (javasolt)
```json
{
  "event_id": "uuid",
  "event_type": "OrderCreated",
  "occurred_at": "ISO8601",
  "version": 1,
  "producer": "outbox-worker",
  "trace_id": "request-id-or-generated",
  "data": { ... }
}
```

#### `OrderCreated` data
```json
{
  "order_id": "uuid",
  "user_id": "uuid",
  "currency": "HUF",
  "total_amount": 11170,
  "items": [
    { "sku": "SKU-001", "qty": 2, "unit_price": 1590 }
  ]
}
```

#### `OrderPaid` / `OrderCanceled`
- legalább `order_id`, `user_id`, `total_amount`, `currency`
- opcionálisan items (tanulás: payload méret vs feldolgozás)

**Validáció consumer oldalon**
- schema verzió (version) ellenőrzés
- required field ellenőrzés
- ismeretlen event_type -> DLQ

Topic: `orders.dlq`  
- ide kerül a hibás event, plusz `error_reason`

---

### 4) Read model / stats API

#### MongoDB `sku_stats`
Kulcs: `(sku, window_start)` (unique index)

Dokumentum:
```json
{
  "sku": "SKU-001",
  "window_start": "ISO8601",
  "window_end": "ISO8601",
  "qty_sum": 42,
  "revenue_sum": 666000,
  "updated_at": "ISO8601"
}
```

#### `GET /stats/sku`
Query:
- `from` (ISO8601, required)
- `to` (ISO8601, required)
- `sku` (optional; ha nincs, top N)
- `limit` (default 20, max 100)

Response:
```json
{
  "items": [
    { "sku": "SKU-001", "window_start": "...", "qty_sum": 10, "revenue_sum": 15900 }
  ]
}
```

Validáció:
- `from < to`
- max range pl. 7 nap (tanulási limit)
- limit tartomány

---

## Repo struktúra és konvenciók

```
/apps
  /api
    /app
      main.py
      settings.py
      api/ (routers)
      domain/
      db/
      security/
      cache/
  /outbox-worker
  /stream-job
  /web
/infra
/scripts
```

Konvenciók:
- Pydantic v2: request/response modellek külön modulban
- DB modellek és migrations: egyértelmű mapping
- “Service layer”: üzleti szabályok, tranzakciók
- “Repository layer”: DB műveletek
- “Transport layer”: FastAPI routerek

---

## Docker Compose baseline

### Cél
Minden komponens külön konténerben, reprodukálható indítás, healthcheck.

### Kötelező elemek a compose-ban
- `healthcheck` minden stateful service-nek
- belső hálózat: `appnet`
- csak `api`, `web`, UI-k publikálnak portot hostra
- volume-ok: postgres, redis, mongo (persist), flink checkpoint path (tanulás)

### Ellenőrzés
- `docker compose up -d`
- `docker compose ps`
- `curl http://localhost:8000/healthz`

---

# Roadmap lépésről lépésre

> Minden lépésnél: **Cél**, **Implementálandó**, **Mit validálj**, **Ellenőrzés**.

---

## 00 – Toolchain, minőségkapuk

### Cél
Automatikus minőség: format, lint, typecheck, teszt.

### Implementálandó
- Python: `ruff` (lint+format), `mypy`, `pytest`
- Node: `eslint`, `prettier`
- pre-commit hook (opcionális, de erős)

### Ellenőrzés
- `ruff check .` és `ruff format .`
- `mypy apps/api`
- `pytest -q`

---

## 01 – PostgreSQL + Alembic + DB sémák

### Cél
Stabil relációs modell + migrációs workflow.

### Implementálandó

#### Táblák (javasolt oszlopok)
1) `users`
- `id uuid pk`
- `email text unique not null`
- `password_hash text not null`
- `role text not null` (check constraint: in ('user','admin'))
- `created_at timestamptz not null default now()`

2) `orders`
- `id uuid pk`
- `user_id uuid not null fk users(id)`
- `status text not null` (check constraint)
- `currency text not null`
- `total_amount bigint not null`
- `idempotency_key uuid not null`
- `created_at timestamptz not null default now()`
- unique: `(user_id, idempotency_key)`

3) `order_items`
- `id uuid pk`
- `order_id uuid not null fk orders(id) on delete cascade`
- `sku text not null`
- `qty int not null`
- `unit_price bigint not null`
- index: `(order_id)`, `(sku)`

4) `refresh_tokens`
- `id uuid pk`
- `user_id uuid not null fk users(id) on delete cascade`
- `token_hash text not null unique`
- `expires_at timestamptz not null`
- `revoked_at timestamptz null`
- `created_at timestamptz not null default now()`

5) `outbox_events`
- `id uuid pk`
- `aggregate_type text not null` (pl. 'order')
- `aggregate_id uuid not null`
- `event_type text not null`
- `payload_json jsonb not null`
- `created_at timestamptz not null default now()`
- `published_at timestamptz null`
- `publish_attempts int not null default 0`
- `last_error text null`
- index: `(published_at, created_at)`

#### Alembic beállítások
- `env.py`:
  - `target_metadata` bekötés
  - db url env varból
- “autogenerate” használata + kézi review
- downgrade útvonal ellenőrzése

### Mit validálj (DB oldalon)
- check constraint status/role enumokra
- unique constraint idempotency-re
- not null mezők

### Ellenőrzés
- `alembic upgrade head`
- `psql`-ben `\dt` és nézd meg constraint-eket
- rollback: `alembic downgrade -1` majd vissza

---

## 02 – FastAPI skeleton + config + logging

### Cél
Fusson az API, legyen config és konzisztens hibaformátum.

### Implementálandó

#### Settings (Pydantic Settings)
- `DATABASE_URL`
- `REDIS_URL`
- `JWT_SECRET`
- `ACCESS_TTL_SECONDS` (900)
- `REFRESH_TTL_SECONDS` (1209600)
- `CORS_ORIGINS` (pl. http://localhost:5173)
- `ENV` (dev/prod)

#### Middleware
1) request-id:
- ha van `X-Request-Id` header, használd; különben generálj UUID
- tedd response headerbe is

2) security headers:
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Referrer-Policy: no-referrer`
- (később: CSP a frontenddel együtt)

#### Error handling
- egységes JSON:
```json
{ "error": { "code": "SOME_CODE", "message": "human readable", "request_id": "..." } }
```

#### Health endpoint
`GET /healthz`:
- Postgres ping (SELECT 1)
- Redis ping (ha már van)
- Kafka ping (opcionális, kezdetben elég config check)

### Mit validálj
- config hiány esetén fail-fast startupkor

### Ellenőrzés
- `curl /healthz` -> 200, JSON
- `curl /openapi.json`

---

## 03 – Auth: JWT access+refresh, RBAC

### Cél
Biztonságos regisztráció/login/refresh/logout.

### Implementálandó

#### Regisztráció
- email unique ellenőrzés
- password hash (argon2)
- role: mindig `user` (admin csak seed scriptből, vagy env var “ALLOW_ADMIN_BOOTSTRAP=true”)

#### Login
- verify password
- generate access JWT:
  - claims: `sub`=user_id, `email`, `role`, `iat`, `exp`, `jti`
- refresh token:
  - random 32+ bytes (base64url)
  - store hash a DB-ben (pl. sha256), `expires_at`
  - response: cookie (httpOnly, SameSite=Lax devben), vagy body (dev)
- session binding (opcionális):
  - store user agent hash / ip (tanulás: tradeoff)

#### Refresh
- refresh token hash lookup
- revoked/expired check
- one-time use:
  - mark current as revoked_at = now()
  - issue new refresh token row

#### Logout
- refresh token revoke

#### RBAC
- dependency: `require_role("admin")`
- `GET /admin/orders` csak admin

### Mit validálj
- password policy
- token exp
- refresh one-time use
- bruteforce mitigation (rate limit később, de design most)

### Ellenőrzés
- register -> login -> me -> refresh -> me -> logout -> refresh fail

---

## 04 – Orders API: CRUD + idempotencia + outbox írás

### Cél
Orders domain működik, outbox event generálódik.

### Implementálandó

#### `POST /orders` részletek
- Header `Idempotency-Key` kötelező
- payload validáció (items, sku regex, qty range)
- számold `total_amount` és `line_total`

**Idempotencia logika**
- Ha `(user_id, idempotency_key)` létezik:
  - ha a request payload hash egyezik (tárolhatod orders táblában `request_hash` mezővel): return ugyanaz a response (200 vagy 201; tanulási célból 200)
  - ha nem egyezik: 409

**Tranzakció**
- insert order
- insert order_items
- insert outbox_event:
  - `event_type=OrderCreated`
  - `payload_json` az event envelope `data` része vagy teljes envelope (dönts és dokumentáld; javasolt teljes envelope)

#### `GET /orders`
- cursor pagination: `created_at,id`
- status filter

#### `GET /orders/{id}`
- jogosultság ellenőrzés
- Redis cache még nem kell itt, de a felület később használja

#### `PATCH /orders/{id}/status`
- státusz átmenet validáció (FSM)
- tranzakció: update + outbox_event (OrderPaid/OrderCanceled)

### Mit validálj
- authorization (saját order)
- status transition
- idempotencia conflict

### Ellenőrzés
- create order -> list -> get -> pay -> get
- DB: outbox sorok megjelennek

---

## 05 – Redis: cache-aside + rate limit + token revoke minta

### Cél
Redis 3 tipikus use-case.

### Implementálandó

#### 1) Cache-aside: order details
- kulcs: `order:{order_id}`
- érték: JSON response
- TTL: 60s
- flow:
  - GET /orders/{id}:
    - redis GET
    - ha hit: return
    - ha miss: DB -> redis SETEX -> return
- invalidáció:
  - PATCH status után `DEL order:{id}`

**Validáció**
- cache méret limit (max payload) – tanulás: large object kerülése

#### 2) Rate limit login
- kulcs: `rl:login:{ip}:{minute}`
- limit: 10/min
- 429 response standard hibával

#### 3) Token denylist (opcionális minta)
- access token jti denylist TTL-ig
- logoutnál: add jti -> redis TTL exp-ig
- auth dependency ellenőrzi jti-t

### Ellenőrzés
- GET order kétszer -> második gyorsabb (log alapján “cache hit”)
- login brute -> 429

---

## 06 – Kafka: topicok, producer/consumer, DLQ

### Cél
Kafka infrastruktúra és alapfogalmak.

### Implementálandó
- Topic creation (compose init vagy startup script):
  - `orders.events` partitions=3, replication=1
  - `orders.dlq` partitions=3
- Producer config:
  - `acks=all`
  - idempotence (ha librdkafka)
- Consumer alap (debug tool): kcat

### Mit validálj
- message key: order_id
- event envelope fieldek (event_type, occurred_at, version)

### Ellenőrzés
- kcat consume: látod a published eventet (07 után lesz teljes)

---

## 07 – Outbox worker: poll, publish, retry

### Cél
Outbox -> Kafka megbízható publish.

### Implementálandó

#### Poll query (tanulás: concurrency-safe)
- `FOR UPDATE SKIP LOCKED`
- batch size: 50
- csak `published_at IS NULL`

#### Publish flow
1. begin tx
2. select batch lockolva
3. commit tx (vagy tx-ben maradva, de publish külső IO: óvatos)
4. minden eventre:
   - publish Kafka
   - ha success: update `published_at=now()`
   - ha fail: increment `publish_attempts`, `last_error`, backoff

**Retry policy**
- max attempts: 10
- exponential backoff: `min(2^attempts, 300s)`
- ha max: küldd DLQ-ba, vagy jelöld “dead” állapotra (pl. `dead_at` mező)

**Idempotencia**
- event_id legyen deterministic: outbox row id
- consumer oldalon is idempotens feldolgozás (Flink/Mongo upsert kulcs)

### Ellenőrzés
- create order -> outbox row -> worker publish -> published_at kitöltődik
- Kafka topicban event megjelenik

---

## 08 – Flink: stream feldolgozás + window + state + checkpoint

### Cél
Stateful stream processing gyakorlat.

### Implementálandó

#### Input
- Kafka source: `orders.events`
- parse JSON, filter: csak `OrderCreated` (tanulás: több event_type kezelése)

#### Transform
- flatMap itemsre: `(sku, qty, revenue=qty*unit_price)`
- window: tumbling 1 minute event time vagy processing time (tanulás: különbség)
- aggregate: sum qty, sum revenue

#### Output
Opció A (egyszerű): Kafka sink `orders.sku-stats`  
Opció B (komplettebb): MongoDB sink (upsert)

Javaslat tanuláshoz: **A majd B**:
- először output topic: könnyű debug kcat-tel
- majd egy kis consumer vagy Flink sink MongoDB-be

#### Checkpointing
- enable checkpointing (pl. 10s)
- state backend: alap
- checkpoint dir volume-ra

### Mit validálj
- rossz JSON -> DLQ vagy skip (log)
- window output helyesség (két order ugyanabban a percben összeadódik)

### Ellenőrzés
- Flink UI: job RUNNING
- kcat consume `orders.sku-stats` -> látod aggregátumokat

---

## 09 – MongoDB: audit + read model + upsert

### Cél
NoSQL használat 2 mintára.

### Implementálandó

#### 1) Audit store
Collection: `order_events`
- insert-only
- index: `order_id`, `occurred_at`

Dokumentum:
```json
{ "order_id": "...", "event_type": "...", "occurred_at": "...", "data": {...} }
```

#### 2) Read model
Collection: `sku_stats`
- unique index: `(sku, window_start)`
- upsert:
  - ha létezik: set qty_sum, revenue_sum, updated_at
  - ha nincs: insert

### Mit validálj
- upsert kulcsok
- indexek tényleg létrejöttek

### Ellenőrzés
- `mongosh` query: `sku_stats.find().limit(5)`

---

## 10 – React/Vite + shadcn/ui: auth flow + táblák + űrlapok

### Cél
Modern UI, minimál feature set.

### Implementálandó

#### Stack (javaslat)
- React + TS + Vite
- React Router
- TanStack Query
- react-hook-form + zod
- shadcn/ui + Tailwind
- toast: shadcn Sonner/Toaster (a shadcn mintáit követve)

#### Oldalak
1) `/login`
- mezők: email, password
- validáció:
  - email formátum
  - password min 1 char (frontend ne duplikálja túl a backend policy-t)
- submit -> /auth/login
- success -> redirect `/orders`

2) `/orders`
- table: id, status, total_amount, created_at
- query params:
  - status filter dropdown
  - pagination “load more” cursorral

3) `/orders/:id`
- details view + status change gomb (pay/cancel)
- optimistic update (TanStack Query mutation)
- error toast

4) `/stats`
- grafikon opcionális (tanulás): táblázat is ok
- lekérdezés `/stats/sku?from=&to=`

#### Auth kezelés
Tanulási javaslat:
- access token memória (state), refresh httpOnly cookie
- axios/ky interceptor:
  - 401 -> refresh -> retry
- XSS tanulság: miért rossz localStorage access tokenhez

### Ellenőrzés
- login -> orders list -> create order (form) -> list update
- stats oldal adatot mutat (Flink után)

---

## 11 – Observability: metrics + UI-k

### Cél
Lásd a rendszer állapotát.

### Implementálandó
- `GET /metrics` (Prometheus format)
- Kafka UI konténer
- Flink UI

### Ellenőrzés
- `/metrics` elérhető
- Kafka UI listáz topicokat
- Flink UI job running

---

## 12 – Security hardening + threat modeling

### Cél
Minimál védelmek ténylegesen működjenek.

### Implementálandó checklist
- Rate limit login
- CORS szigor (csak web origin)
- Cookie beállítások:
  - httpOnly, SameSite=Lax, Secure (prod)
- Input validáció mindenhol
- RBAC a szerveren
- Dependency audit:
  - `pip-audit` / `npm audit`
- Log sanitization:
  - jelszó soha ne logolódjon
  - token se

### Ellenőrzés
- brute force -> 429
- nem admin -> 403 admin endpointon
- rossz payload -> 422

---

## 13 – E2E ellenőrzés: seed + check script

### Cél
Egy paranccsal validálható, hogy minden összekötve.

### Implementálandó
`scripts/seed.sh`
- admin user létrehozása (külön env gate)
- 1–2 order generálás

`scripts/check.sh`
1. healthz
2. login
3. create order (idempotency key)
4. verify outbox published_at (poll psql)
5. verify kafka event (kcat)
6. verify stats output (kcat vagy mongo query)

### Ellenőrzés
- `./scripts/check.sh` exit 0

---

## Gyakori hibák / debug checklist

- **Kafka advertised listeners**: hostról vs hálózatról elérés eltér
- **Alembic async**: env.py konfiguráció
- **CORS + cookie**: `credentials: include` és backend `allow_credentials=True`
- **Flink connector verziók**: kompatibilitás
- **Redis TTL**: cache ne ragadjon be

---

## Továbbfejlesztések
- Schema registry + Avro/Protobuf
- OpenTelemetry tracing
- Inventory service külön mikróként
- Kubernetes deploy

---

## Használati útmutató

1. Haladj sorban.
2. Minden lépés után futtasd az ellenőrzést.
3. Ha elakadsz: logs + kcat + psql + flink ui a 4 alap debug eszköz.

---

*Vége.*
