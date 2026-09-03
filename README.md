# Accounting Automation

Indian SMB accounting automation: WhatsApp invoice capture, AI extraction, double-entry ledger, GST, and reporting.

## Documentation

| Document | Role |
|----------|------|
| [PRD.md](PRD.md) + [PRD_SUPPLEMENT.md](PRD_SUPPLEMENT.md) | Requirements (**FROZEN**) |
| [PRD_DECISIONS.md](PRD_DECISIONS.md) | Ratified Q&A (40 decisions) |
| [PRD_REVIEW.md](PRD_REVIEW.md) | Gap analysis |
| [ARCHITECTURE.md](ARCHITECTURE.md) | System architecture |
| [TECHNICAL_DESIGN.md](TECHNICAL_DESIGN.md) | Implementation design |
| [PILOT.md](PILOT.md) | Pilot runbook |
| [DEPLOYMENT.md](DEPLOYMENT.md) | Production deployment |

## Quick start

```bash
pip install -e ".[dev]"
export DATABASE_URL=sqlite:///./dev.db  # or use docker compose
python -c "from app.core.database import Base, engine; import app.models.entities; Base.metadata.create_all(engine)"
uvicorn app.main:app --reload
pytest tests/ -v
```

## Docker

```bash
docker compose up --build
```

API: http://localhost:8000/docs

## Key principles

- **Accounting engine first** — AI never posts without domain validation
- **Debit = credit** enforced before every post
- **Human confirmation** required before post (Phase 1)
- **Provider abstraction** — swap WhatsApp, Claude, storage without touching domain code
- **Idempotency** — retried jobs cannot double-post
