# Security, Audit & Reliability

**Stage:** 15 of 18

## Authentication

| Surface | Control |
|---------|---------|
| REST API | JWT bearer (`Authorization: Bearer`) |
| WhatsApp webhook | HMAC-SHA256 (`X-Hub-Signature-256`) when `WHATSAPP_APP_SECRET` set |
| Dev bypass | Signature skipped only when app secret unset (logs warning) |

## Authorization

- `OrganizationContext` scopes all repository queries
- Cross-tenant COA access rejected at domain layer
- Roles: owner, accountant, viewer, admin **(IMP-DEFAULT)**

## Tenant isolation

- Every tenant table has `organization_id`
- Services validate resource org matches context
- Tests: `test_tenant_isolation_on_coa`

## Financial traceability

```
JournalEntry → source_type/source_id → Invoice → Document → AIExtractionRecord
              → AuditLogEntry (posted action)
              → ApprovalRequest (confirmation)
```

## Idempotency

- Journal: `(organization_id, idempotency_key)` unique
- Journal: `(organization_id, source_type, source_id)` unique
- Jobs: `(organization_id, idempotency_key)` unique
- Tests: `test_idempotency_prevents_duplicate_post`

## Background jobs

- States: QUEUED, RUNNING, SUCCEEDED, FAILED, RETRYING
- Dead letter: `dead_letter_at` after max retries
- Financial jobs check idempotency before post

## Secrets

- All credentials via environment variables
- Never commit `.env` (see `.gitignore`)

## Document access

- Storage keys prefixed with `organization_id`
- Local dev: filesystem under `LOCAL_STORAGE_PATH`
- Production: S3-compatible with versioning

## PII / logging

- Do not log full extraction payloads in production
- Anthropic calls contain invoice PII — DPA required before pilot

## Pre-pilot checklist

See [DEPLOYMENT.md](DEPLOYMENT.md) security checklist.
