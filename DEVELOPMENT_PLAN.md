# Development Plan

**Stage:** 6 of 18

Vertical slices in dependency order. Each milestone has a deliverable and gate.

| Milestone | Deliverable | Gate | Status |
|-----------|-------------|------|--------|
| M1 Foundation | FastAPI, Postgres, Docker, CI, migrations | App starts, DB connects, tests run | In progress |
| M2 Org & Users | Organization, User, Membership, phone mapping | Tenant isolation tests pass | In progress |
| M3 Accounting Core | COA, JournalEntry, double-entry post | Debit=credit enforced | In progress |
| M4 Documents | Upload, storage, metadata, extraction record | Storage + provenance tests | In progress |
| M5 Invoices | Purchase invoice → proposal → post | End-to-end manual post | In progress |
| M6 Payments | Payment, PaymentApplication | Partial payment tests | Done |
| M6b Bank | Import CSV, auto-reconcile | Match tests | Done |
| M10 Dashboard API | Summary, invoices, payments lists | JWT + role auth | Done |
| M10b Dashboard UI | React SPA: login, overview, invoices, payments | JWT auth flow | Done |
| M13 Phase 3 | Sales invoices, credit/debit notes, GSTR prep, e-invoice | Phase 3 tests pass | Done |
| M14 Phase 4 | TDS compute/apply, compliance calendar | TDS tests pass | Done |
| M7 WhatsApp | Webhook, media, confirmation flow | Mock E2E test | In progress |
| M8 Tax | TaxRuleVersion, basic GST split | Rule version recorded | In progress |
| M9 Reporting | Ledger Excel/PDF export | Output validates | In progress |
| M10 Dashboard API | JWT auth, read endpoints | API integration tests | In progress |
| M11 Hardening | Audit, idempotency, DLQ | Security checklist | Done |
| M12 Pilot | PILOT.md runbook | Real workflow checklist | Documented |
| M13 Production | DEPLOYMENT.md, CI deploy | Health checks pass | Done |

## Build order (critical path)

1. Accounting engine (M3) — before AI/WhatsApp
2. Document pipeline with mock AI (M4)
3. Invoice posting (M5)
4. Jobs + idempotency (M1/M11)
5. WhatsApp adapter (M7)
6. Tax layer (M8)
7. Reporting (M9)
8. Dashboard reads (M10)

## Out of scope for initial implementation

- Live Claude API in CI (mock adapter only)
- Live WhatsApp in CI (mock adapter)
- GSP production credentials (sandbox stub)
- E-invoice NIC integration (interface only)
- Full GSTR return filing

## Phase mapping **(IMP-DEFAULT Q-02)**

**Phase 1 pilot:** M1–M5, M7 (mock), M8 (basic), M11  
**Phase 2:** M6, M9, M10, live adapters, Celery scale-up  
**Phase 3:** E-invoice, GSTR-1/3B prep, sales invoices, credit/debit notes, search — **Done (API)**  
**Phase 4:** TDS computation, compliance calendar — **Done (API + UI)**  
**Phase 5:** Production hardening — migrations, health probes, CI, rate limits — **Done**
