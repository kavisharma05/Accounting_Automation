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

## Docker Compose (development)

```bash
docker compose up --build
```

Services: `api` (port 8000), `worker`, `db`, `redis`.

## Database migrations

```bash
# Development bootstrap
python -c "from app.core.database import Base, engine; Base.metadata.create_all(engine)"

# Production
alembic upgrade head
```

## Health checks

- `GET /api/v1/health` → 200 `{"status":"ok"}`
- Worker process running: `python -m app.workers.runner`

## Monitoring

- Structured application logs
- Sentry DSN (optional) for error tracking
- Alert on: dead-letter jobs, 5xx rate, DB connection failures

## Backups

- PostgreSQL: daily automated backup (managed provider or pg_dump cron)
- Object storage: versioning enabled on bucket
- RPO target: 24h **(IMP-DEFAULT)**
- RTO target: 4h **(IMP-DEFAULT)**

## Rollback

1. Revert container image to previous tag
2. Run `alembic downgrade -1` only if migration is backward-compatible
3. Verify health endpoint and sample ledger query

## Security checklist (pre-production)

- [ ] WhatsApp webhook signature verification enabled (`WHATSAPP_APP_SECRET`)
- [ ] JWT secret rotated from dev default
- [ ] Database credentials in secret manager
- [ ] HTTPS termination at load balancer
- [ ] Rate limiting on webhooks (TBD implementation)
- [ ] PII not logged in extraction payloads
- [ ] Tenant isolation tests passing in CI
