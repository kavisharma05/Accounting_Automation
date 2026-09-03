# PRD Decisions (Ratified)

**Status:** Ratified — agent judgment per product owner delegation (2026-09-03)  
**Authority:** Resolves all open questions in [PRD_REVIEW.md](PRD_REVIEW.md)  
**Companion:** Missing PRD content is in [PRD_SUPPLEMENT.md](PRD_SUPPLEMENT.md)

These decisions are **binding for implementation** unless explicitly overridden by the product owner.

---

## Blockers (Q-01 – Q-08)

### Q-01 — PRD completeness

**Decision:** The original [PRD.md](PRD.md) is an **incomplete fragment**. Proceed with **PRD.md + PRD_SUPPLEMENT.md** as the ratified requirements set. No separate “baseline” document exists; supplement replaces it.

### Q-02 — Phase definitions

| Phase | Scope |
|-------|--------|
| **Phase 1 — Pilot MVP** | Multi-tenant orgs; WhatsApp purchase invoices; AI extraction (Claude); human confirmation; purchase invoice posting; basic GST on lines; minimal COA seed; ledger PDF/Excel; phone→org auth; Redis/RQ jobs; sandbox e-way bill stub; REST setup API |
| **Phase 2** | Dashboard UI; JWT auth for all API; bank statement import; payment + partial application; reconciliation; email reports to CA; period locking; Celery scale-up if needed |
| **Phase 3** | E-invoice via GSP; GSTR-1/3B **preparation** (not filing); advanced search; sales invoices; credit/debit notes workflow |
| **Phase 4** | TDS computation; compliance calendar automation |
| **Phase 5** | Production hardening; hosting re-evaluation; performance; DPDP audit; optional Postgres RLS |

### Q-03 — Phase 1 job infrastructure

**Decision:** **Redis + RQ from Phase 1** with DB-tracked job state, idempotency keys, retry (max 3), and dead-letter (`dead_letter_at`). Resolves CON-01 in favor of PRD line 7.

### Q-04 — Phase 1 authentication & authorization

| Surface | Mechanism |
|---------|-----------|
| WhatsApp inbound | Meta webhook HMAC (`X-Hub-Signature-256`); sender phone must exist in `phone_org_mappings` with `verified_at` set |
| Financial post | Same registered phone must send `YES` / `CONFIRM` / `OK` to approve pending `ApprovalRequest` |
| Setup / admin API | JWT bearer; claims: `sub` (user), `org_id`, `role` |
| Unregistered phone | Outbound message: “Phone not registered”; no financial effect |

### Q-05 — Debit = credit

**Decision:** **Explicit product requirement.** Enforced in **domain layer** (`AccountingEngine`) before post. DB check constraints on line non-negativity; application validates sum equality. Posted entries are immutable.

### Q-06 — AI confirmation vs auto-post

**Decision:** **Always require human confirmation in Phase 1.** `auto_post_confidence_threshold = 0`. Auto-post may be evaluated in Phase 2 pilot data review; not Phase 1.

### Q-07 — Tax liability boundary

| Capability | Phase |
|------------|-------|
| Compute GST on invoice lines | Phase 1 |
| Record tax rule version + snapshot on transaction | Phase 1 |
| Prepare GSTR worksheets | Phase 3 |
| File returns on behalf of client | **Out of scope** until legal/compliance review |

**Disclaimer (required in product):** Tool assists bookkeeping; CA must verify before filing.

### Q-08 — GST returns in Phase 1

**Decision:** **None.** Phase 1 records GST on invoices only. No GSTR-1/2B/3B in Phase 1.

---

## High priority (Q-09 – Q-20)

| # | Decision |
|---|----------|
| Q-09 | **Unified `Party`** entity with `party_type`: customer, vendor, both |
| Q-10 | **Roles:** `owner` (all), `accountant` (post, approve, export), `viewer` (read-only), `admin` (DLQ, org config). WhatsApp users act as `accountant` unless mapped otherwise later |
| Q-11 | **Immutable posted entries;** corrections via **reversal journal entry** only |
| Q-12 | **Indian FY:** April 1 – March 31; `financial_year_start_month = 4`. Period locking deferred to Phase 2 |
| Q-13 | **Accrual basis** Phase 1; cash basis Phase 3 |
| Q-14 | **Both:** `tax_rule_version_id` FK + `tax_computation_snapshot` JSONB on invoice |
| Q-15 | **Pilot/dev:** local filesystem adapter. **Production:** Cloudflare R2 (S3-compatible, versioned). Host bundled disk **rejected** (CON-03) |
| Q-16 | **MasterGST** as default GSP; Masters India as backup adapter |
| Q-17 | **Application-layer** org scoping on all repositories (Phase 1). Postgres RLS evaluated Phase 5 |
| Q-18 | **Phase 1 reports:** General ledger, trial balance (simple), invoice list. Phase 2: P&L, balance sheet, GST summary |
| Q-19 | **Phase 1 search:** none (API list filters only). Phase 3: Postgres FTS on invoice number, party name, vendor GSTIN, document hash |
| Q-20 | **Duplicate invoice:** reject if same org + party + invoice_number + invoice_date. **Duplicate payment:** reject same org + party + amount + payment_date + reference if reference provided |

---

## Medium priority (Q-21 – Q-36)

| # | Decision |
|---|----------|
| Q-21 | OCR fallback when Claude confidence < 0.5 OR Claude API error after 1 retry; then Tesseract text passed to classification (Phase 2: full OCR pipeline) |
| Q-22 | **Single `Invoice` entity** with `invoice_type`: purchase, sales |
| Q-23 | **Typed FKs:** `entity_type` (string) + `entity_id` (UUID) for Anomaly, ApprovalRequest, AuditLogEntry |
| Q-24 | **Phase 2.** Phase 1: full payment against single invoice only in manual API; no partial in WhatsApp flow |
| Q-25 | **Seed minimal Indian COA** on org creation: cash, bank, AR, AP, input GST, output GST, sales, generic expense |
| Q-26 | **INR only** Phase 1–3 |
| Q-27 | **Round to 2 decimal places** (paise); line totals rounded per line; invoice total = sum(lines)+tax; warn if AI total mismatch > ₹1 |
| Q-28 | **Resend** (simpler API; SendGrid as fallback adapter) |
| Q-29 | **Railway** Phase 1–2 (Docker deploy); re-evaluate Phase 5 |
| Q-30 | **Self-hosted JWT** (implemented); managed auth deferred |
| Q-31 | **Data in India-preferred region** when available on host; DPDP: consent at onboarding, deletion on request, minimal PII in logs; full DPDP audit Phase 5 |
| Q-32 | **Retain 8 years** (GST statutory); documents in versioned storage; soft-delete only pre-post |
| Q-33 | **Pilot:** 3–5 orgs, ≤50 invoices/day total, ≤15 users |
| Q-34 | **`EInvoice` table exists** Phase 1 schema; provider unconnected until Phase 3 |
| Q-35 | **One document → one primary transaction** Phase 1; split Phase 3 |
| Q-36 | **Separate keys:** job idempotency (`extract-{document_id}`); journal (`invoice-{id}` or explicit key) |

---

## Low priority (Q-37 – Q-40)

| # | Decision |
|---|----------|
| Q-37 | **Remove “baseline” references** in future PRD edits; supplement is canonical |
| Q-38 | **`/api/v1/`** prefix; webhooks unversioned |
| Q-39 | **CI:** ruff + pytest on every push; ≥80% domain coverage target Phase 2 |
| Q-40 | **Session messages** within 24h window for confirmations; **templates** for outbound >24h (Phase 2) |

---

## Contradiction resolutions

| ID | Resolution |
|----|------------|
| CON-01 | Redis+RQ Phase 1 (see Q-03) |
| CON-02 | Claude is primary variable AI cost; WhatsApp/GSP also variable — document in cost model |
| CON-03 | R2 for production storage; not host disk |
| CON-04 | EInvoice entity yes; provider Phase 3 |
| CON-05 | Phase 1 auth defined (Q-04) |
| CON-06 | Debit=credit in supplement as explicit requirement |
| CON-07 | Search requirements defined in Q-19 |

---

## Freeze recommendation

**FREEZE APPROVED** for **PRD.md + PRD_SUPPLEMENT.md + PRD_DECISIONS.md** as the requirements baseline for pilot and Phase 1 implementation.

Product owner may amend any decision with a dated entry in this file.
