# Claude Code – Python FastAPI Project Guidelines

This file defines **mandatory rules** for all code generation and modifications in this FastAPI codebase.
If any rule would be violated, stop and fix the solution to fully comply with these guidelines.

---

## 0) Global Principles (always)

- If **"create skeleton"** is requested, create a **minimal FastAPI** project:
  - One runnable app (`app/main.py`) with a single `GET /health` or `GET /` endpoint returning simple JSON.
  - Do **not** add extra features, packages, auth, database, migrations, admin UI.
  - Keep it **as simple as possible**.

- **Type hints everywhere**.
  - Every public function/method must have annotations.
  - Prefer `pydantic` models for request/response DTOs.

- Prefer **many small, short functions** over a few large ones.

- **NO automated tests**:
  - Do not generate unit/integration/e2e tests.
  - Remove any test scaffolding from templates (e.g., `tests/`, `test_*.py`, pytest config).

- **Environment variables via `.env`**:
  - Always provide `.env.example` (placeholders only, no secrets).
  - Never commit secrets.

- If any implementation decision or uncertainty arises, **ASK BEFORE coding**.
  - Examples: auth strategy, data model, DB (yes/no), caching, pagination, error format, background jobs.

---

## 1) Mandatory Stack & Technical Rules

- Web framework: **FastAPI**
- ASGI server: typically `uvicorn` (only when run instructions are needed)
- Validation:
  - **Pydantic (v2)** for request/response models.
  - Validate inputs for every public endpoint.

- Error handling:
  - Use consistent HTTP status codes.
  - Do not swallow exceptions; log and return clean errors.

- Naming:
  - `snake_case` for files/modules.
  - `PascalCase` for classes/models.

---

## 2) Mandatory Folder Structure

Keep it simple; avoid over-architecture.

Recommended:

- `app/main.py` – FastAPI app, router wiring
- `app/api/` – routes (routers)
- `app/schemas/` – Pydantic models (DTOs)
- `app/services/` – business logic/use-cases (framework-agnostic)
- `app/repositories/` – data access (only if needed)
- `app/core/` – config, logging, shared utilities

Rules:
- Route modules must be **thin**: request/response + call services.
- Business logic must **not** live inside endpoint functions.

---

## 3) Config & Env

- All env vars in `.env` and `.env.example`.
- Prefer `app/core/config.py` with Pydantic Settings for loading + validation.
- `.env.example` includes names + placeholders only:
  - `APP_ENV=development`
  - `APP_PORT=8000`
  - (if used) `DATABASE_URL=postgresql+psycopg://user:pass@host:5432/db`

---

## 4) Documentation (mandatory)

- `README.md` lists **features only** in short bullet points.
- If endpoints exist, mention them briefly (e.g., `/health`).
- List required env var names (no values).

---

## 5) Workflow Rules (mandatory before coding)

For every task:

1. Describe in **3–7 bullet points** what will be created/changed (files, routes, models, services).
2. If a decision point exists, **stop and ask**.
3. After implementation:
   - Remove test-related artifacts.
   - Verify structure (thin routes, services hold logic).
   - Update README feature list.
   - Verify `.env.example` completeness.

---

## 6) Forbidden / Avoid

- Any testing frameworks/configs/files.
- Unstructured business logic inside endpoints.
- Secrets committed into the repo.
- Unnecessary abstraction when a minimal solution is sufficient.

---
