# Staging Deployment

Deploy a production-like stack locally or on a staging VM using Docker Compose with mock providers (no WhatsApp/Claude credentials required).

## Prerequisites

- Docker and Docker Compose v2
- OpenSSL (to generate `SECRET_KEY`)

## One-command deploy

```bash
cp .env.staging.example .env.staging
# Edit .env.staging — set SECRET_KEY=$(openssl rand -hex 32)

chmod +x scripts/staging_up.sh scripts/staging_verify.sh
./scripts/staging_up.sh
./scripts/staging_verify.sh
```

## What starts

| Service | Purpose |
|---------|---------|
| `db` | PostgreSQL 16 |
| `redis` | Job queue |
| `api` | FastAPI + built dashboard (port 8000) |
| `worker` | Background job processor |
| `seed` | One-shot pilot org (via `--profile tools`) |

Staging overlay (`docker-compose.staging.yml`) adds:

- `restart: unless-stopped` on all services
- API healthcheck on `/api/v1/health/ready`
- `ENVIRONMENT=staging` (startup validation runs only for `production`)
- Alembic migrate on API boot

## Access

| URL | Purpose |
|-----|---------|
| http://localhost:8000 | Dashboard (built into API image) |
| http://localhost:8000/docs | OpenAPI |
| http://localhost:8000/api/v1/health/ready | Readiness probe |

**Login:** `admin@pilot.local` / `pilot-admin-change-me`

## Enable real adapters (optional)

Edit `.env.staging`:

```bash
MESSAGING_PROVIDER=whatsapp
DOCUMENT_PROVIDER=claude
ANTHROPIC_API_KEY=sk-...
WHATSAPP_APP_SECRET=...
WHATSAPP_ACCESS_TOKEN=...
WHATSAPP_PHONE_NUMBER_ID=...
```

Set `ENVIRONMENT=production` only when all production secrets are configured (enables strict startup validation).

## Teardown

```bash
docker compose -f docker-compose.yml -f docker-compose.staging.yml down
# Add -v to remove postgres volume
```

## Next: production

See [DEPLOYMENT.md](DEPLOYMENT.md) for the security checklist and production hosting.
