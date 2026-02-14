# Security Checklist (Step 12)

## Auth & Session
- [x] Login rate limit (`/auth/login`)
- [x] Refresh token stored in httpOnly cookie
- [x] Access token short TTL (configurable)
- [ ] Refresh token rotation tested under load

## CORS & Cookies
- [x] CORS allowlist (`cors_origins`)
- [x] `allow_credentials=True`
- [ ] `SameSite=Strict` in prod (currently `Lax`)
- [ ] `Secure` cookies in prod

## RBAC & Permissions
- [x] Role‑based gate in `admin` endpoint
- [ ] 403 verified for non‑admin user
- [ ] Audit logs for admin actions (optional)

## Input Validation
- [x] Pydantic validation for requests
- [ ] Explicit constraints on all public endpoints

## Secrets & Config
- [ ] `.env` never committed (verify .gitignore)
- [ ] Rotate JWT secret for production
- [ ] Separate prod vs dev configs

## Dependency Hygiene
- [ ] `pip-audit` (API + workers)
- [ ] `npm audit` (web)

## Logging & Error Handling
- [x] Structured error responses
- [ ] Redact tokens/passwords from logs
- [ ] Request ID correlation in logs

## Transport Security
- [ ] HTTPS in prod (reverse proxy)
- [ ] HSTS

## Data
- [ ] DB backups (Postgres + Mongo)
- [ ] PII minimization / retention policy

## Quick Commands
```
# API rate limit check
for i in $(seq 1 11); do
  curl -s -o /dev/null -w "%{http_code}\n" \
    -X POST http://localhost:18000/auth/login \
    -H 'content-type: application/json' \
    -d '{"email":"u1@example.com","password":"bad"}'
done

# CORS check (should include your frontend origin)
curl -I http://localhost:18000/healthz
```
