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

## Dashboard UI

React + TypeScript SPA in `frontend/`.

**Development** (API on :8000, Vite dev server on :5173 with proxy):

```bash
# Terminal 1 — API
uvicorn app.main:app --reload

# Terminal 2 — seed pilot org + user (once)
python scripts/seed_pilot_org.py

# Terminal 3 — dashboard
cd frontend && npm install && npm run dev
```

Open http://localhost:5173 — login with `admin@pilot.local` / `pilot-admin-change-me` (from seed script).

**Screens:** Overview, Invoices (search + filter), Payments (record + apply), Bank (CSV import + reconcile), GSTR (3B summary + Excel export).

**Production / Docker** — frontend is built into the API image and served at http://localhost:8000/:

```bash
docker compose up --build -d
docker compose --profile tools run --rm seed
```

Or use the `frontend` compose service for hot-reload during development.

## Pilot (next step)

```bash
docker compose up --build -d
python scripts/pilot_smoke_test.py --base-url http://localhost:8000
```

See [PILOT.md](PILOT.md) for full onboarding checklist.

## Phase 3 API (sales, notes, GSTR, e-invoice)

| Endpoint | Purpose |
|----------|---------|
| `POST .../sales-invoices` | Create sales invoice |
| `POST .../sales-invoices/{id}/post` | Post sales invoice |
| `POST .../credit-notes` | Create credit note against invoice |
| `POST .../credit-notes/{id}/post` | Post credit note |
| `POST .../debit-notes` | Create debit note against invoice |
| `POST .../debit-notes/{id}/post` | Post debit note |
| `GET .../gstr/gstr1` | GSTR-1 B2B worksheet data |
| `GET .../gstr/gstr3b` | GSTR-3B summary |
| `GET .../reports/gstr1.xlsx` | GSTR-1 + 3B Excel export |
| `POST .../invoices/{id}/einvoice` | Generate e-invoice IRN (mock GSP) |
| `GET .../search/invoices?q=` | Search invoices by number/party/GSTIN |

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
