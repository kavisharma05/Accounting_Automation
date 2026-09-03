# Production Deployment

**Stage:** 18 of 18

## Pipeline

```
Code → CI (GitHub Actions) → Docker build → Deploy → Migrate → Health check → Monitor
```

## Environment variables

| Variable | Required | Notes |
|----------|----------|-------|
| `DATABASE_URL` | Yes | PostgreSQL connection string |
| `REDIS_URL` | Yes | Job queue |
| `SECRET_KEY` | Yes | Strong random value |
| `ANTHROPIC_API_KEY` | Prod AI | Omit for mock |
| `WHATSAPP_*` | Prod WhatsApp | verify token, app secret, access token, phone id |
| `S3_*` or `LOCAL_STORAGE_PATH` | Yes | Versioned object storage in prod |
| `MESSAGING_PROVIDER` | Yes | `whatsapp` or `mock` |
| `DOCUMENT_PROVIDER` | Yes | `claude` or `mock` |
| `ENVIRONMENT` | Prod | `production` enables startup validation |
| `RUN_MIGRATIONS` | Docker | `true` (default) runs `alembic upgrade head` on boot |
| `WEBHOOK_RATE_LIMIT_PER_MINUTE` | No | Default 120 |

## Docker Compose (development)

```bash
docker compose up --build
```

Services: `api` (port 8000), `worker`, `db`, `redis`.

## Health checks

| Endpoint | Purpose |
|----------|---------|
| `GET /api/v1/health` | Basic status |
| `GET /api/v1/health/live` | **Liveness** — process up (K8s/load balancer) |
| `GET /api/v1/health/ready` | **Readiness** — PostgreSQL + Redis reachable (503 if degraded) |

- Worker process: `python -m app.workers.runner`

## Database migrations

```bash
# Development
python scripts/init_db.py

# Production (Docker entrypoint runs this automatically)
alembic upgrade head

# Dev fallback without Alembic
python scripts/init_db.py --create-all
```

Set `RUN_MIGRATIONS=false` to skip migrations in Docker entrypoint.

## Security checklist (pre-pilot)

Use this before exposing the app to real users or WhatsApp traffic.

| Item | Action |
|------|--------|
| Secrets | Generate a strong `SECRET_KEY`; never use `change-me` in production |
| Environment | Set `ENVIRONMENT=production` to enable startup validation |
| Providers | Use real `MESSAGING_PROVIDER` / `DOCUMENT_PROVIDER` only with valid API keys |
| WhatsApp | Configure `WHATSAPP_APP_SECRET` so webhook HMAC verification is enforced |
| Rate limit | Tune `WEBHOOK_RATE_LIMIT_PER_MINUTE` (default 120) for expected traffic |
| TLS | Terminate HTTPS at load balancer or reverse proxy |
| Database | Restrict PostgreSQL to private network; use managed backups |
| Redis | Restrict Redis to private network; no public exposure |
| Storage | Use versioned S3-compatible storage; block public ACLs |
| JWT | Rotate `SECRET_KEY` invalidates existing tokens — plan maintenance window |
| Logging | Avoid logging full document payloads or PII in production |
| Migrations | Run `alembic upgrade head` before traffic; verify with `/api/v1/health/ready` |

See also [SECURITY.md](SECURITY.md) for auth, tenant isolation, and idempotency details.
