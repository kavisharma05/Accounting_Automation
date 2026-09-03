# Technical Design

**Status:** Implementation baseline  
**Stage:** 3 of 18  
**Inputs:** [PRD.md](PRD.md), [ARCHITECTURE.md](ARCHITECTURE.md)

Implementation defaults marked **(IMP-DEFAULT)** are chosen where PRD is silent; see [PRD_REVIEW.md](PRD_REVIEW.md) for ratification.

---

## Backend structure

```
app/
├── main.py                 # FastAPI app factory
├── api/
│   ├── deps.py             # DI: db session, org context, providers
│   ├── v1/
│   │   ├── router.py
│   │   └── routes/         # REST endpoints
│   └── webhooks/
│       └── whatsapp.py
├── core/
│   ├── config.py           # pydantic-settings
│   ├── database.py         # SQLAlchemy engine/session
│   ├── security.py         # JWT, webhook HMAC
│   ├── exceptions.py       # DomainError hierarchy
│   └── logging.py
├── domain/
│   ├── accounting/         # JournalEntry rules, posting
│   ├── tax/                # GST computation
│   ├── documents/          # Extraction validation
│   └── organizations/      # Tenant context
├── services/               # Orchestration (thin)
├── repositories/           # Data access, tenant-scoped
├── integrations/
│   ├── protocols.py        # Provider ABCs
│   ├── messaging/
│   ├── document_understanding/
│   ├── ocr/
│   ├── email/
│   ├── storage/
│   └── gsp/
├── models/                 # SQLAlchemy ORM
├── schemas/                # Pydantic request/response
└── workers/
    ├── queue.py            # RQ setup
    ├── jobs.py             # Job definitions + idempotency
    └── runner.py
```

## Layering rules

| Layer | Calls | Never calls |
|-------|-------|-------------|
| `api` | `services`, `schemas` | `models` directly, vendor SDKs |
| `services` | `domain`, `repositories`, `integrations.protocols` | vendor SDKs |
| `domain` | pure Python + decimal | DB, HTTP |
| `repositories` | `models`, SQLAlchemy | business rules |
| `integrations/*` | vendor SDKs/HTTP | `domain` internals |

## Dependency injection

`app/api/deps.py` exposes FastAPI `Depends`:

- `get_db()` → `Session`
- `get_org_context()` → `OrganizationContext` (from JWT or webhook phone map)
- `get_*_provider()` → concrete adapter from settings

Provider selection via `Settings`:

```python
MESSAGING_PROVIDER=whatsapp|mock
DOCUMENT_PROVIDER=claude|mock
STORAGE_PROVIDER=s3|local
```

## Configuration

`app/core/config.py` — environment-driven:

| Variable | Purpose |
|----------|---------|
| `DATABASE_URL` | PostgreSQL |
| `REDIS_URL` | Job queue |
| `SECRET_KEY` | JWT signing |
| `ANTHROPIC_API_KEY` | Claude adapter |
| `WHATSAPP_*` | Meta Cloud API |
| `S3_*` | Object storage |
| `GSP_*` | E-way bill sandbox |

## Error handling

```python
class DomainError(Exception): ...
class ValidationError(DomainError): ...
class PostingError(DomainError): ...
class IdempotencyConflict(DomainError): ...
class TenantIsolationError(DomainError): ...
```

API maps to HTTP:

| Error | Status |
|-------|--------|
| `ValidationError` | 422 |
| `PostingError` | 400 |
| `IdempotencyConflict` | 409 |
| `TenantIsolationError` | 403 |
| Unhandled | 500 (logged, no stack to client) |

## API versioning

Prefix: `/api/v1/`. Webhooks: `/webhooks/whatsapp` (unversioned, signature-verified).

## Authentication strategy

| Surface | Phase 1 **(IMP-DEFAULT)** |
|---------|---------------------------|
| REST API | JWT bearer; `sub` = user_id; claim `org_id` |
| WhatsApp | Webhook HMAC + registered phone → org mapping |
| Admin DLQ | JWT with `role=admin` |

Dashboard auth (Phase 2+): same JWT stack extended with refresh tokens.

## AI extraction pipeline

```
Document (bytes)
  → Pre-processing (mime detect, optional resize)
  → DocumentUnderstandingProvider.extract_document()
  → Pydantic InvoiceExtraction schema validation
  → Confidence evaluation (field completeness + model confidence)
  → Anomaly flags (total mismatch, missing GSTIN)
  → AccountingClassificationService.propose()
  → ApprovalRequest if required
  → User confirmation
  → AccountingEngine.post()
  → JournalEntry
```

Provenance: every extraction creates `AIExtractionRecord` (provider, model, raw JSON, confidence, timestamp).

## Background processing

**IMP-DEFAULT:** Redis + RQ from Phase 1 (resolves CON-01 vs PRD line 7).

```
QUEUED → RUNNING → SUCCEEDED
                 → FAILED → RETRYING → RUNNING
                          → FAILED (max) → dead_letter_at set
```

Job record table: `background_jobs` with `idempotency_key` unique per org.

Financial jobs check idempotency before domain post.

## Idempotency

- Jobs: `(organization_id, idempotency_key)` unique
- Posts: `(organization_id, source_type, source_id)` unique on `journal_entries`

## Testing strategy

- Unit: domain accounting (debit=credit, reversals)
- Integration: repositories with PostgreSQL (docker-compose test DB)
- Adapter: mock providers only in CI
- Financial: duplicate post, partial payment scenarios

## Logging

Structured JSON logs; never log full invoice PII or secrets. Request ID in context var.
