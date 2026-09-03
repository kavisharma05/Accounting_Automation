# Accounting Automation

Indian SMB accounting automation: WhatsApp invoice capture, AI extraction, double-entry ledger, GST, and reporting.

## Documentation

| Stage | Document |
|-------|----------|
| 1 | [PRD_REVIEW.md](PRD_REVIEW.md) |
| 2 | [ARCHITECTURE.md](ARCHITECTURE.md) |
| 3 | [TECHNICAL_DESIGN.md](TECHNICAL_DESIGN.md) |
| 4 | [DOMAIN_DB.md](DOMAIN_DB.md) |
| 5 | [INTEGRATION_CONTRACTS.md](INTEGRATION_CONTRACTS.md) |
| 6 | [DEVELOPMENT_PLAN.md](DEVELOPMENT_PLAN.md) |
| 16 | [PILOT.md](PILOT.md) |
| 18 | [DEPLOYMENT.md](DEPLOYMENT.md) |

## Quick start

```bash
pip install -e ".[dev]"
export DATABASE_URL=sqlite:///./dev.db  # or use docker compose
python -c "from app.core.database import Base, engine; Base.metadata.create_all(engine)"
uvicorn app.main:app --reload
pytest tests/ -v
```

## Docker

```bash
docker compose up --build
```

API: http://localhost:8000/docs

## Project layout

```
app/
├── api/           # REST + webhooks
├── core/          # config, db, security
├── domain/        # accounting & tax engines
├── integrations/  # provider adapters
├── models/        # SQLAlchemy ORM
├── services/      # orchestration
└── workers/       # RQ background jobs
tests/
```

## Key principles

- **Accounting engine first** — AI never posts without domain validation
- **Debit = credit** enforced before every post
- **Provider abstraction** — swap WhatsApp, Claude, storage without touching domain code
- **Idempotency** — retried jobs cannot double-post
