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

## Pilot (next step)

```bash
docker compose up --build -d
python scripts/pilot_smoke_test.py --base-url http://localhost:8000
```

See [PILOT.md](PILOT.md) for full onboarding checklist.

## Phase 2 API (dashboard, payments, bank)

| Endpoint | Purpose |
|----------|---------|
| `GET .../dashboard` | Summary metrics |
| `GET .../invoices` | Invoice list with outstanding |
| `POST .../payments` | Post payment with partial applications |
| `POST .../bank-accounts/{id}/import` | CSV bank statement import |
| `POST .../bank-accounts/{id}/reconcile` | Auto-match to payments |
| `PATCH .../period-lock` | Lock posting through date |
| `POST .../reports/email-ledger` | Email Excel to CA |

## Key principles

- **Accounting engine first** — AI never posts without domain validation
- **Debit = credit** enforced before every post
- **Human confirmation** required before post (Phase 1)
- **Provider abstraction** — swap WhatsApp, Claude, storage without touching domain code
- **Idempotency** — retried jobs cannot double-post
