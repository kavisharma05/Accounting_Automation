# PRD Supplement

**Status:** Ratified companion to [PRD.md](PRD.md)  
**Decisions:** [PRD_DECISIONS.md](PRD_DECISIONS.md)  
**Date:** 2026-09-03

This document supplies the content absent from the uploaded PRD fragment. Together with PRD.md, it forms the **frozen requirements baseline**.

---

## Product vision

**Product:** WhatsApp-first accounting automation for Indian small businesses.

**Problem:** Owners send invoice photos on WhatsApp; bookkeepers re-key data into Tally/Excel. Errors, delays, and missing audit trails are common.

**Solution:** User forwards invoice → AI extracts fields → user confirms in WhatsApp → system posts double-entry ledger with GST → CA exports reports.

**Success (Phase 1 pilot):**

- ≥90% extraction accuracy on vendor, total, date (human-verified sample)
- Zero duplicate posts from retries
- Zero cross-tenant incidents
- <5 min median time from photo to posted entry (excluding user think time)

---

## Personas

| Persona | Needs |
|---------|--------|
| **Business owner** | Send invoice photos via WhatsApp; confirm postings |
| **Bookkeeper / accountant** | Review extractions; export ledger; manage COA |
| **Chartered Accountant (CA)** | Reliable Excel/PDF exports; tax snapshot on invoices |
| **System admin** | Register phones; monitor dead-letter jobs |

---

## Principles

| # | Principle |
|---|-----------|
| P1 | Vendor independence — domain has zero vendor SDK imports |
| P2 | Documents are the audit backbone — durable versioned storage |
| P3 | AI proposes; domain disposes — no AI direct ledger writes |
| P4 | Debit = credit before every post |
| P5 | Financial idempotency on jobs and journal sources |
| P6 | Tenant isolation by organization |
| P7 | Tax rule version + snapshot recorded on each taxed transaction |
| P8 | Human confirmation before post (Phase 1) |

---

## Phase 1 functional requirements

### FR-1 WhatsApp ingestion

- Accept image/PDF invoice via WhatsApp Cloud API webhook
- Verify webhook signature when app secret configured
- Resolve sender phone → organization via verified mapping
- Download and store document with SHA-256 dedup hash

### FR-2 AI extraction

- Primary: Claude Sonnet vision via `DocumentUnderstandingProvider`
- Output validated against Pydantic schema
- Persist `AIExtractionRecord` (provider, model, fields, confidence, timestamp)
- Flag anomaly if extracted total ≠ line sum beyond ₹1 tolerance

### FR-3 Human confirmation

- Send summary message with vendor, number, amount
- Accept `YES`, `CONFIRM`, or `OK` from same registered phone
- Create `ApprovalRequest` while pending

### FR-4 Purchase invoice posting

- Create purchase invoice from extraction
- Compute GST (CGST/SGST default; IGST if interstate flag set manually Phase 1)
- Post journal entry: Debit expense + input GST; Credit payables
- Enforce duplicate invoice rule (party + number + date)

### FR-5 Organization setup (API)

- Create organization, seed minimal COA
- Register phone mapping
- Create chart of accounts extensions

### FR-6 Reporting

- Export general ledger as Excel and PDF

### FR-7 Background jobs

- States: QUEUED, RUNNING, SUCCEEDED, FAILED, RETRYING
- Idempotency keys; dead-letter after 3 failures

### Out of scope Phase 1

- Sales invoices via WhatsApp
- GSTR filing or preparation
- E-invoice IRN generation
- Bank reconciliation
- Dashboard UI
- Auto-post without confirmation
- Multi-currency

---

## Non-functional requirements

| NFR | Requirement |
|-----|-------------|
| Availability | Best-effort pilot; 99% target Phase 5 |
| Latency | Extraction job p95 < 60s |
| Backup | Daily Postgres backup; RPO 24h |
| Security | Webhook HMAC; JWT for API; tenant-scoped queries |
| Retention | 8 years financial + document retention |
| Observability | Structured logs + Sentry free tier |

---

## API architecture

```
/api/v1/
  GET  /health
  POST /organizations
  POST /organizations/{id}/accounts
  POST /organizations/{id}/phone-mappings
  POST /organizations/{id}/journal-entries
  POST /auth/login
  GET  /organizations/{id}/reports/ledger.xlsx
  GET  /organizations/{id}/reports/ledger.pdf

/webhooks/
  GET|POST /whatsapp
```

Layering: API → Services → Domain → Repositories → PostgreSQL. Business logic never in route handlers.

---

## Search requirements (Phase 3)

Postgres FTS on: invoice number, party name, GSTIN, document SHA-256. Filters: date range, status, party. No Elasticsearch until >100k invoices/org.

---

## Accounting requirements (explicit)

1. Every `JournalEntry` must have ≥2 lines
2. `SUM(debit) = SUM(credit)` before status → posted
3. Posted entries are immutable; reversals only via reversal entry
4. Each posted invoice/expense links to exactly one journal entry
5. Idempotency: same source_type + source_id cannot post twice

---

## Tax requirements (Phase 1)

- Apply `TaxRuleVersion` effective on invoice date
- Store `tax_rule_version_id` and `tax_computation_snapshot` on invoice
- Default GST rate 18% if no rule loaded
- Tool **does not file** returns (see PRD_DECISIONS Q-07)

---

## Authentication (Phase 1)

See PRD_DECISIONS Q-04. Dashboard JWT extended Phase 2 for all management functions.

---

## Edge cases — accepted / deferred

| Case | Phase 1 behavior |
|------|------------------|
| Blurry photo | Low confidence → ask user to re-send |
| Duplicate upload (same SHA) | Skip re-extraction; link existing document |
| Wrong confirmation | User contacts support; reversal entry Phase 1 manual API |
| Closed period | Not enforced Phase 1 |
| Partial payment | Phase 2 |
| Composition scheme invoice | Flag anomaly; manual review |

---

## Report set

**Phase 1:** General ledger, invoice register (API list), Excel/PDF export  
**Phase 2:** Trial balance, P&L, balance sheet, GST summary for CA email  
**Phase 3:** GSTR-1 draft worksheet export

---

## Document index

| File | Role |
|------|------|
| [PRD.md](PRD.md) | Original technology + entity fragment |
| [PRD_SUPPLEMENT.md](PRD_SUPPLEMENT.md) | Vision, functional reqs, NFRs (this file) |
| [PRD_DECISIONS.md](PRD_DECISIONS.md) | All Q&A ratified |
| [PRD_REVIEW.md](PRD_REVIEW.md) | Gap analysis (historical) |
| [ARCHITECTURE.md](ARCHITECTURE.md) | System architecture |
| [TECHNICAL_DESIGN.md](TECHNICAL_DESIGN.md) | Implementation design |
