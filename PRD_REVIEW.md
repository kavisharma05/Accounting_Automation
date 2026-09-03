# PRD Review

**Document reviewed:** [PRD.md](PRD.md)  
**Review date:** 2026-09-03  
**Review scope:** Stage 1 — PRD validation / gap review only. No application code, architecture, or schema work.  
**Review rule:** Nothing in this document is treated as a decided requirement unless it is explicitly stated in PRD.md. Gaps are recorded as gaps; suggested clarifications are labelled as unratified options.

---

## Verdict and Freeze Recommendation

**Verdict: DO NOT FREEZE.**

PRD.md is a **115-line fragment** of what appears to be a larger document. It begins at `### Background Processing` (line 3) with no product vision, personas, functional requirements, or non-functional requirements. It references sections, principles, phases, and a "baseline" document that are **not present in the repository**.

What the file *does* contain is useful but incomplete:

- Background job state and idempotency requirements (line 7)
- Provider abstraction interfaces (line 11)
- A conceptual entity list (lines 16–18)
- Technology selection rationale (lines 23–115)

**Approximately 80–90% of a complete PRD is absent.** Architecture, technical design, database schema, API contracts, and implementation cannot proceed responsibly until the missing content is supplied or explicitly written and ratified.

**Recommended next step:** Upload or author the missing PRD sections (or confirm this fragment is the complete intentional scope), resolve the Questions / Decisions Required section at the end of this document, then re-run this review before freezing.

---

## What Was Reviewed

### Scope

| Item | Detail |
|------|--------|
| File | [PRD.md](PRD.md) — sole requirements document in repository |
| Lines | 115 |
| Sections present | Background Processing, Integration Architecture, Database Model, Technology Selection and Cost Strategy (Backend through Messaging) |
| Sections absent | Everything preceding Background Processing; API Architecture; Search (functional spec); Principles; Phase definitions; functional requirements for all product features |

### Evidence of truncation / corruption

| ID | Finding | PRD citation | Severity | Blocks freeze |
|----|---------|--------------|----------|---------------|
| STR-01 | Document opens at `### Background Processing` with no `##`-level structure and no content before line 3 | lines 1–3 | Blocker | Yes |
| STR-02 | Internal link `[API Architecture](#api-architecture)` targets a section not in the file | line 33 | Blocker | Yes |
| STR-03 | Internal link `[Search](#search)` targets a section not in the file | line 112 | Blocker | Yes |
| STR-04 | "Principle 2" cited for storage requirements; no principles section exists | line 75 | Blocker | Yes |
| STR-05 | Phases 1, 2+, 3+, 5 referenced throughout; no phase definitions exist | lines 11, 57, 66, 90, 100, 112 | Blocker | Yes |
| STR-06 | "the baseline" / "baseline's own analysis" cited ~20 times as authority; baseline document not in repository | lines 23, 49, 51, 57, 62, 90, 115 | Blocker | Yes |
| STR-07 | "the defined report set" referenced; report set not defined | line 97 | High | Yes |
| STR-08 | "the defined Search requirements" referenced; search requirements not defined | line 112 | High | Yes |
| STR-09 | "explicitly out of scope for this document per the final instruction" — instruction not present | line 15 | Medium | Yes |
| STR-10 | Integration Architecture table collapsed onto a single line (line 11); markdown tables may not render | line 11 | Low | No |

### What was *not* reviewed

No code, tests, migrations, or prior design documents exist in the repository. This review is limited to PRD.md only.

---

## Requirements Coverage

Legend: **Present** = explicitly stated in PRD.md · **Partial** = mentioned but insufficient to implement · **Absent** = not stated (not invented here)

### Product definition

| Domain | Status | PRD evidence | Gap summary |
|--------|--------|--------------|-------------|
| Product vision / problem statement | Absent | — | No "why" or target outcome |
| Target users / personas | Absent | — | No SME owner, bookkeeper, CA, admin personas |
| Success metrics / KPIs | Absent | — | No extraction accuracy, posting latency, pilot criteria |
| Scope boundaries (in / out) | Partial | line 15 (schema out of scope only) | Feature scope undefined |
| Phase roadmap definitions | Absent | phases referenced, never defined | lines 11, 57, 66, 90, 100, 112 |

### Functional — messaging & input

| Domain | Status | PRD evidence | Gap summary |
|--------|--------|--------------|-------------|
| WhatsApp inbound message handling | Absent | `MessagingProvider` named only | line 11 |
| WhatsApp outbound / confirmation flow | Absent | — | No conversation UX |
| User confirmation before posting | Absent | — | Critical for financial safety |
| Phone number → organization mapping | Absent | — | Tenant binding undefined |
| Multi-channel messaging (future) | Partial | line 115 (native app mentioned) | No requirements |

### Functional — documents & AI

| Domain | Status | PRD evidence | Gap summary |
|--------|--------|--------------|-------------|
| Document upload / storage | Partial | `Document` entity, `StorageProvider` | lines 16, 75 |
| AI extraction pipeline | Partial | `DocumentUnderstandingProvider`, `AIExtractionRecord` | lines 11, 16 |
| OCR fallback trigger conditions | Absent | Tesseract named as fallback | line 57 — when does fallback run? |
| Confidence thresholds / human review | Absent | `Anomaly`, `ApprovalRequest` entities named | line 16 — no rules |
| Extraction provenance fields | Partial | `AIExtractionRecord (provenance)` named | line 16 — fields undefined |
| Supported document types | Absent | — | PDF, photo, handwritten? |

### Functional — accounting

| Domain | Status | PRD evidence | Gap summary |
|--------|--------|--------------|-------------|
| Double-entry ledger | Partial | `JournalEntry`, `JournalEntryLine`, debit=credit mentioned in tech rationale | lines 16–18, 42 — not stated as product requirement |
| Chart of accounts management | Partial | `ChartOfAccount` entity | line 16 — structure, seeding undefined |
| Purchase / sales invoices | Partial | `Invoice`, `InvoiceLineItem` | line 16 — lifecycle undefined |
| Expenses | Partial | `Expense` entity | line 16 |
| Credit / debit notes | Partial | entities named | line 16 — application rules undefined |
| Payments & applications | Partial | `Payment`, `PaymentApplication` (many-to-many) | line 18 |
| Posting / immutability / reversal | Absent | "once posted, exactly one JournalEntry" | line 18 — correction model undefined |
| Period close / financial year | Absent | — | Indian April–March not mentioned |
| Bank reconciliation | Partial | `BankAccount`, `BankStatementTransaction`, `ReconciliationMatch` | line 16 — matching rules undefined |

### Functional — tax & compliance

| Domain | Status | PRD evidence | Gap summary |
|--------|--------|--------------|-------------|
| GST computation (CGST/SGST/IGST) | Absent | — | |
| TDS computation | Absent | `TaxRuleVersion (GST/TDS config)` | line 16 — no rules |
| E-way bill generation | Partial | `GspProvider`, `EWayBill` | lines 11, 16 — workflow undefined |
| E-invoicing | Partial | `EInvoiceProvider` unimplemented Phase 1 | line 11 |
| GSTR returns / filing | Absent | — | |
| Compliance calendar | Partial | `ComplianceCalendarEntry` entity | line 16 — content undefined |
| Tax rule versioning audit trail | Partial | lookup + result recorded on transaction | line 18 — storage mechanism undefined |

### Functional — reporting & search

| Domain | Status | PRD evidence | Gap summary |
|--------|--------|--------------|-------------|
| Report types | Absent | "defined report set" referenced | line 97 |
| Report delivery (email to CA) | Partial | Resend/SendGrid for "CA-facing report" | line 82 |
| Search requirements | Absent | Postgres FTS recommended | line 112 — what is searchable? |

### Functional — administration

| Domain | Status | PRD evidence | Gap summary |
|--------|--------|--------------|-------------|
| User / org management | Partial | `Organization`, `User`, `OrganizationMembership` | line 16 |
| Roles & permissions | Partial | "role" on membership | line 16 — roles undefined |
| Audit log | Partial | `AuditLogEntry` entity | line 16 — events undefined |
| Notifications | Partial | `Notification` entity | line 16 |
| Anomaly handling | Partial | `Anomaly` entity | line 16 — workflow undefined |
| Admin dead-letter surfacing | Partial | dead-letter "surfaced to an admin" | line 7 — UI/alert undefined |

### Non-functional requirements

| Domain | Status | PRD evidence | Gap summary |
|--------|--------|--------------|-------------|
| Background job reliability | Present | state machine, retry, idempotency, dead-letter | line 7 |
| Provider replaceability | Present | zero domain dependency on vendor SDKs | line 11 |
| Multi-tenancy isolation | Partial | every entity → `Organization` | line 18 — enforcement mechanism undefined |
| Authentication | Partial | dashboard auth Phase 2+ | line 100 — Phase 1 auth undefined |
| Performance / SLA / latency | Absent | — | |
| Availability / uptime | Absent | — | |
| Backup / disaster recovery | Absent | — | |
| Data retention / residency | Absent | — | |
| Observability | Partial | structured logging + Sentry | line 107 |

### Technology decisions (present and relatively complete)

| Domain | Status | PRD evidence |
|--------|--------|--------------|
| Backend: FastAPI | Present | lines 25–33 |
| Database: PostgreSQL | Present | lines 35–43 |
| AI: Claude Sonnet vision | Present | lines 45–53 |
| OCR fallback: Tesseract | Present | lines 55–62 |
| Queue: Celery/RQ Phase 2+ | Present | lines 64–71 |
| Storage: S3-compatible | Present | lines 73–78 |
| Email: Resend/SendGrid | Present | lines 80–86 |
| Hosting: Railway/Render | Present | lines 88–93 |
| Reporting libs: pandas/openpyxl/reportlab | Present | lines 95–98 |
| Search: Postgres FTS | Present | lines 110–113 |
| Messaging: WhatsApp Cloud API | Present | lines 11, 115 |

---

## Ambiguities

| ID | Ambiguity | PRD citation | Severity | Blocks freeze |
|----|-----------|--------------|----------|---------------|
| AMB-01 | `TaxRuleVersion` "is not linked to individual transactions directly" but "the result of that lookup (which rule version was applied) is recorded on the transaction" — FK to version row, immutable computation snapshot, or both? | line 18 | High | Yes |
| AMB-02 | `Party` may be one entity with type flag or two entities — affects schema, queries, and GSTIN handling | line 16 | Medium | Yes |
| AMB-03 | `Anomaly` / `ApprovalRequest` / `AuditLogEntry` polymorphic vs typed FKs — affects referential integrity | line 18 | Medium | Yes |
| AMB-04 | `OrganizationMembership` has "role" but no role names or permission matrix | line 16 | High | Yes |
| AMB-05 | "Invoice (purchase/sale)" — single `Invoice` entity with type flag or separate entities? | line 16 | Medium | Yes |
| AMB-06 | When does `OcrFallbackProvider` (Tesseract) activate vs primary Claude extraction? | lines 11, 57 | Medium | Yes |
| AMB-07 | "MasterGST/Masters India sandbox" — which GSP vendor is Phase 1 default? | line 11 | Medium | Yes |
| AMB-08 | "Resend or SendGrid" — equal alternatives with no selection criteria | line 82 | Low | No |
| AMB-09 | "Railway or Render" — equal alternatives with no selection criteria | line 90 | Low | No |
| AMB-10 | "Self-hosted auth using FastAPI-native JWT/session handling, or an open-source auth toolkit, or a managed provider" — three undecided options | line 102 | Medium | Yes |
| AMB-11 | "Small-business multi-tenant scale" — no tenant count, invoice volume, or concurrency defined | lines 40, 93 | Medium | Yes |
| AMB-12 | `Document` → "one or more" source documents per invoice/expense — can one document map to multiple transactions? | line 18 | Medium | Yes |
| AMB-13 | `Invoice`/`Expense`/etc. → "once posted, exactly one JournalEntry" — can a journal entry aggregate multiple invoices? | line 18 | Medium | Yes |

### Contradictions

| ID | Contradiction | PRD citations | Severity | Blocks freeze |
|----|---------------|---------------|----------|---------------|
| CON-01 | **Background job requirements vs Phase 1 queue strategy.** Line 7 mandates tracked states (`QUEUED`/`RUNNING`/…), automatic retry with backoff, idempotency keys, and dead-letter surfacing. Line 66 states Phase 1 needs only "synchronous/simple async via FastAPI background tasks" which provides none of the above. | lines 7, 66 | Blocker | Yes |
| CON-02 | **Variable cost claim.** Line 50 states Claude API is "the one genuinely variable cost line in the whole stack." WhatsApp Cloud API (line 115) and GSP per-transaction fees (line 11) are also per-use costs not accounted for. | lines 50, 11, 115 | Medium | No |
| CON-03 | **Storage durability vs hosting bundled storage.** Line 75 requires "durable, versioned storage, not local disk, even in pilot" but permits "the hosting provider's bundled storage" (line 75) on Railway/Render (line 90), which is typically ephemeral/non-versioned disk. | lines 75, 90 | High | Yes |
| CON-04 | **`EInvoice` entity vs `EInvoiceProvider` unimplemented.** Entity listed in core set (line 16); provider explicitly not connected Phase 1 (line 11). Unclear whether entity/table exists before integration. | lines 11, 16 | Medium | Yes |
| CON-05 | **Authentication deferred vs financial actions in Phase 1.** Dashboard auth is Phase 2+ (line 100). WhatsApp is Phase 1 primary channel (line 115). No Phase 1 auth model for actions that create financial records. | lines 100, 115 | Blocker | Yes |
| CON-06 | **Postgres debit=credit enforcement vs schema deferred.** Line 42 claims Postgres can enforce debit=credit "via constraints/transactions" but line 15 explicitly defers schema. The enforcement mechanism is asserted but not specified as a requirement. | lines 15, 42 | Medium | Yes |
| CON-07 | **Search adequacy vs undefined search requirements.** Line 112 claims Postgres FTS is "adequate for the defined Search requirements" but those requirements do not exist in the document. | line 112 | High | Yes |

---

## Missing Decisions

These are architectural or product choices the PRD explicitly defers or leaves open. Each requires a human decision before design can proceed.

| ID | Decision needed | PRD citation | Blocks |
|----|-----------------|--------------|--------|
| DEC-01 | Resolve CON-01: Phase 1 job infrastructure — full queue (Redis/Celery/RQ) with state tracking, or defer job requirements to Phase 2? | lines 7, 66 | Architecture, reliability |
| DEC-02 | Resolve CON-05: Phase 1 authentication and authorization model (WhatsApp-only? API keys? org binding?) | lines 100, 115 | Security, all features |
| DEC-03 | `Party` model: unified entity with type flag vs separate Customer/Vendor entities | line 16 | Schema, API |
| DEC-04 | Polymorphic vs typed FKs for `Anomaly`, `ApprovalRequest`, `AuditLogEntry` | line 18 | Schema, queries |
| DEC-05 | Role names and permission matrix for `OrganizationMembership` | line 16 | Auth, dashboard |
| DEC-06 | Tax rule audit storage: FK vs snapshot vs both | line 18 | Tax engine, audit |
| DEC-07 | GSP vendor selection: MasterGST vs Masters India | line 11 | Integration |
| DEC-08 | Storage provider selection: Cloudflare R2 vs host bundled vs MinIO | lines 75, 90 | Pilot deployment |
| DEC-09 | Email provider: Resend vs SendGrid | line 82 | Integration |
| DEC-10 | Hosting provider: Railway vs Render | line 90 | Deployment |
| DEC-11 | Phase definitions: what ships in Phase 1, 2, 3, 5? | multiple | Entire roadmap |
| DEC-12 | Product scope: computation/preparation only vs actual GST filing? | implied by entities | Legal liability |
| DEC-13 | Invoice model: single entity with type vs separate purchase/sale | line 16 | Schema, workflows |
| DEC-14 | OCR fallback activation criteria | lines 11, 57 | AI pipeline |
| DEC-15 | Confirmation UX: always confirm before post, or auto-post above confidence threshold? | — (not in PRD) | Core workflow |

---

## Technical Risks

| ID | Risk | Basis | Severity | Mitigation requires |
|----|------|-------|----------|---------------------|
| TEC-01 | Building on incomplete requirements produces rework across all layers | STR-01 through STR-09 | Blocker | Complete PRD |
| TEC-02 | Phase 1 without job queue violates stated reliability requirements if CON-01 unresolved | lines 7, 66 | High | DEC-01 |
| TEC-03 | Provider abstraction interfaces named but method signatures, error contracts, and idempotency semantics undefined | line 11 | High | API contract design |
| TEC-04 | Multi-tenancy enforcement unspecified — application-layer scoping vs Postgres RLS | line 18 | High | Security architecture |
| TEC-05 | No API versioning strategy mentioned despite `#api-architecture` reference | line 33 | Medium | Architecture doc |
| TEC-06 | Celery/RQ deferred but 9 async job types listed for Phase 1 workloads | lines 5, 66 | High | DEC-01 |
| TEC-07 | Hosting on Railway/Render may not meet data residency or compliance needs — not evaluated | lines 90, 93 | Medium | Compliance decision |
| TEC-08 | Claude pricing assumed "trivial" at pilot volume but not quantified; no budget cap or fallback if costs spike | lines 49–50 | Medium | Cost model |
| TEC-09 | No migration / schema versioning strategy despite Postgres being chosen | lines 35–43 | Medium | Tech design |
| TEC-10 | No CI/CD, testing, or deployment requirements in PRD | — | Medium | Tech design |
| TEC-11 | Single-line markdown tables (line 11) may indicate document export corruption — requirements may be misread | line 11 | Low | PRD cleanup |

---

## Accounting Risks

| ID | Risk | Basis | Severity |
|----|------|-------|----------|
| ACC-01 | Debit = credit invariant mentioned only in technology rationale (line 42), not as an enforceable product requirement | line 42 vs line 18 | Blocker |
| ACC-02 | No rule for posted entry immutability; corrections via reversal vs edit undefined | line 18 | High |
| ACC-03 | No financial year / period locking (Indian April–March) | — | High |
| ACC-04 | No currency handling (INR-only assumed? multi-currency?) | — | Medium |
| ACC-05 | No rounding rules for line items vs invoice totals vs tax amounts | — | High |
| ACC-06 | No duplicate invoice detection (same vendor + invoice number + date) | — | High |
| ACC-07 | No duplicate payment detection | — | High |
| ACC-08 | Partial payment, over-payment, and advance payment rules undefined despite `PaymentApplication` many-to-many | line 18 | High |
| ACC-09 | Credit note / debit note application against invoices undefined | line 16 | High |
| ACC-10 | Chart of accounts structure (standard Indian COA seed? custom only?) undefined | line 16 | Medium |
| ACC-11 | Accrual vs cash basis accounting not specified | — | High |
| ACC-12 | Opening balances / migration from existing books undefined | — | Medium |
| ACC-13 | AI must never post without domain validation — stated in workflow guidance but **not in PRD** | — | Blocker |
| ACC-14 | No requirement that journal entry creation is idempotent (only jobs have idempotency keys) | line 7 | High |
| ACC-15 | Bank reconciliation matching rules (exact amount? fuzzy date? split transactions?) undefined | line 16 | Medium |

---

## Tax & Compliance Risks

| ID | Risk | Basis | Severity |
|----|------|-------|----------|
| TAX-01 | No GST mechanics defined: CGST/SGST/IGST split, place of supply, reverse charge | line 16 (entity only) | Blocker |
| TAX-02 | No HSN/SAC code requirements or validation | — | High |
| TAX-03 | No composition scheme handling | — | Medium |
| TAX-04 | No input tax credit eligibility rules | — | High |
| TAX-05 | No TDS sections, rates, thresholds, or Form 26AS reconciliation | line 16 (TDS in entity name only) | High |
| TAX-06 | No TCS requirements | — | Medium |
| TAX-07 | E-way bill: threshold, validity, cancellation, extension rules undefined | lines 5, 11, 16 | High |
| TAX-08 | E-invoice: turnover applicability (₹5 Cr threshold), IRN generation workflow undefined | lines 11, 16 | High |
| TAX-09 | No GSTR-1/2B/3B preparation or filing scope defined | — | Blocker |
| TAX-10 | Product liability boundary undefined: tool computes vs tool files returns | — | Blocker |
| TAX-11 | `TaxRuleVersion` update process undefined — who publishes new rules? manual import? | line 16 | High |
| TAX-12 | No statutory document retention period (GST: 6 years?) | — | High |
| TAX-13 | DPDP Act 2023 obligations not mentioned (consent, data principal rights) | — | High |
| TAX-14 | Data residency requirements for Indian financial data not specified | — | Medium |
| TAX-15 | CA-facing report content and legal disclaimer undefined | line 82 | Medium |

---

## Security Risks

| ID | Risk | Basis | Severity |
|----|------|-------|----------|
| SEC-01 | No Phase 1 authentication model while WhatsApp can trigger financial actions | lines 100, 115 | Blocker |
| SEC-02 | WhatsApp webhook signature verification not mentioned | — | Blocker |
| SEC-03 | Phone number → organization binding and spoofing/reassignment not addressed | — | Blocker |
| SEC-04 | No authorization model (who can post, approve, view documents, admin dead-letters?) | line 16 (role unnamed) | High |
| SEC-05 | Document access control undefined (signed URLs? expiry? org scoping?) | lines 16, 75 | High |
| SEC-06 | PII in AI prompts (invoice data sent to Anthropic) — no data processing agreement or redaction policy | lines 45–53 | High |
| SEC-07 | Secrets management (API keys for WhatsApp, Claude, GSP) not specified | line 11 | High |
| SEC-08 | Encryption at rest for documents and database not specified | — | Medium |
| SEC-09 | Rate limiting and abuse prevention not specified | — | Medium |
| SEC-10 | Audit log tamper resistance not specified | line 16 | Medium |
| SEC-11 | Logging of sensitive financial data (PII, GSTIN, bank details) not addressed | line 107 | Medium |
| SEC-12 | WhatsApp opt-in / 24-hour customer care window compliance not mentioned | — | Medium |
| SEC-13 | No webhook replay attack prevention beyond idempotency keys | line 7 | Medium |
| SEC-14 | Multi-tenant data leakage prevention mechanism undefined | line 18 | Blocker |

---

## External Dependencies

| ID | Dependency | PRD reference | What must be procured | Lead-time / ops risk | Blocks |
|----|------------|---------------|----------------------|---------------------|--------|
| DEP-01 | Anthropic Claude API (Sonnet, vision) | lines 45–53 | API key, billing account; verify pricing at docs.claude.com | Low; usage-based cost variable | AI extraction |
| DEP-02 | Meta WhatsApp Cloud API | lines 11, 115 | Business verification, phone number, webhook URL, template approval | High (Meta review weeks) | Primary input channel |
| DEP-03 | MasterGST or Masters India (GSP) | line 11 | Commercial agreement, GSTIN auth, sandbox → production | Medium | E-way bill |
| DEP-04 | Resend or SendGrid | line 82 | API key, domain verification (SPF/DKIM) | Low | Email reports |
| DEP-05 | S3-compatible object storage (R2 / host / MinIO) | lines 73–78 | Bucket, credentials, versioning config | Low | Document storage |
| DEP-06 | Railway or Render | lines 88–93 | Account, container deploy config | Low | Hosting |
| DEP-07 | Redis (Phase 2+ queue) | lines 64–71 | Managed Redis or self-hosted | Low | Background jobs |
| DEP-08 | Sentry (monitoring) | line 107 | Project, DSN | Low | Error tracking |
| DEP-09 | Tesseract (OCR fallback) | lines 55–62 | System package / container image | Low | OCR fallback |
| DEP-10 | PostgreSQL managed instance | lines 35–43 | Supabase / Neon / Railway DB | Low | All data |
| DEP-11 | `EInvoiceProvider` (Phase 3+) | line 11 | NIC IRP integration via GSP | High | E-invoicing |
| DEP-12 | Baseline PRD document (referenced, not in repo) | lines 23, 49, etc. | Author must supply | — | Requirements completeness |

---

## Assumptions the PRD Makes Implicitly

These are **not stated as requirements** but are implied by technology choices and entity names. Each should be confirmed or rejected explicitly.

| ID | Implicit assumption | Evidence |
|----|---------------------|----------|
| ASM-01 | Target market is Indian businesses (GST, TDS, e-way bill, e-invoice entities) | lines 11, 16 |
| ASM-02 | Primary user interaction channel is WhatsApp | lines 11, 115 |
| ASM-03 | Users are small businesses ("small-business multi-tenant scale") | lines 40, 93 |
| ASM-04 | Chartered Accountants (CAs) are report recipients | line 82 |
| ASM-05 | Invoices arrive as photos/PDFs needing AI extraction | lines 45–53 |
| ASM-06 | System is multi-tenant SaaS (Organization-scoped entities) | line 18 |
| ASM-07 | INR is the only currency | no mention of others |
| ASM-08 | Accrual accounting is the default | no mention of cash basis |
| ASM-09 | Pilot volume is "a handful of invoices/day" | lines 49, 66 |
| ASM-10 | Team is Python-capable (FastAPI + pandas ecosystem) | lines 25–33, 95–98 |
| ASM-11 | A dashboard will exist (Phase 2+) | lines 33, 100 |
| ASM-12 | Documents must be retained as audit evidence ("audit backbone") | line 75 |
| ASM-13 | AI proposes; human confirms before posting (from workflow guidance, **not in PRD**) | — |

---

## Missing Edge Cases

The PRD does not address these scenarios. They are listed as gaps, not as requirements.

### Document / AI edge cases

- Blurry, rotated, or partial invoice photos
- Handwritten invoices
- Multi-page invoices
- Missing or invalid GSTIN on vendor invoice
- Invoice total ≠ sum of line items (rounding discrepancy)
- Multiple tax rates on one invoice
- Ambiguous vendor (similar names, no GSTIN match)
- Same document submitted twice (duplicate upload)
- Document in regional language
- Password-protected PDF

### Accounting edge cases

- Credit note exceeding original invoice amount
- Debit note on already-paid invoice
- Payment spanning multiple invoices with rounding remainder
- Partial payment followed by credit note
- Invoice dated in closed period
- Expense without supporting document
- Contra entries / internal transfers
- Write-offs and bad debt

### Tax edge cases

- Interstate vs intrastate misclassification by AI
- Reverse charge applicability
- Composition dealer invoices (no GST breakdown)
- B2B vs B2C invoice treatment
- E-way bill not required below threshold — system must not generate unnecessarily
- E-invoice applicable for some customers but not others (turnover threshold)

### Operational edge cases

- WhatsApp message arrives but media download fails
- User confirms wrong extraction
- User sends message from unregistered phone number
- Organization has multiple WhatsApp users with different permissions
- Job retry after partial side effect (document stored but extraction failed)
- GSP sandbox returns success but production would fail
- Tax rule version changes mid-day during batch processing

### Multi-tenancy edge cases

- User belongs to multiple organizations
- Organization deletion with posted journal entries
- Cross-org document or invoice reference (should be impossible)

---

## Recommended Clarifications

These are **unratified suggestions** for PRD authors. They are not requirements and must not be treated as decided.

1. **Restore the full PRD** — upload the complete document including vision, personas, functional requirements, NFRs, principles, phase definitions, API Architecture, and Search sections. Fix markdown table formatting (especially line 11).

2. **Add an explicit accounting invariant requirement:** "A `JournalEntry` may only be posted when `SUM(debits) = SUM(credits)`; this is enforced at the domain layer before persistence and validated by a database constraint where feasible."

3. **Add an explicit AI safety requirement:** "No journal entry may be created from AI extraction without passing domain validation and, unless auto-post criteria are defined and met, explicit user confirmation."

4. **Resolve CON-01 explicitly** — either mandate minimal job infrastructure in Phase 1 (even a simple Redis + RQ setup) or downgrade line 7 job requirements to Phase 2 with a documented Phase 1 exception.

5. **Define Phase 1 MVP scope** as a bounded checklist: e.g., single-org pilot, WhatsApp inbound, AI extraction, manual confirmation, purchase invoice posting, basic GST on invoice lines — with everything else deferred.

6. **Define the product liability boundary** for tax: "computation and record-keeping only" vs "return preparation" vs "filing on behalf of client."

7. **Specify Phase 1 auth:** at minimum, WhatsApp webhook verification + phone-number-to-org binding + confirmation message from known sender.

8. **Define roles:** suggest at minimum `owner`, `accountant`, `viewer`, `admin` — but this is a proposal, not a decision.

9. **Quantify pilot scale:** e.g., 3–5 organizations, ≤50 invoices/day total, ≤10 concurrent users.

10. **Add a "Principles" section** including Principle 2 (document audit backbone) and any others referenced.

---

## Questions / Decisions Required

Answer these before freezing the PRD. Each question links to finding IDs it resolves.

### Blockers — must answer before any design work

| # | Question | Resolves |
|---|----------|----------|
| Q-01 | Is [PRD.md](PRD.md) the complete intentional requirements document, or is there a missing first portion (vision, functional requirements, phases, principles, API Architecture, Search)? If missing, when will it be supplied? | STR-01–STR-09 |
| Q-02 | Define Phase 1, Phase 2, Phase 3, and Phase 5 scope as explicit feature checklists. | STR-05, DEC-11 |
| Q-03 | Phase 1 job infrastructure: implement full state-tracked queue (Redis + RQ/Celery) per line 7, or defer those requirements and accept FastAPI background tasks with documented limitations? | CON-01, DEC-01, TEC-02, TEC-06 |
| Q-04 | Phase 1 authentication and authorization: how is a WhatsApp sender authenticated and authorized to post financial entries for an organization? | CON-05, DEC-02, SEC-01–SEC-04, SEC-14 |
| Q-05 | Is debit = credit enforcement a explicit product requirement? Where is it enforced (domain layer, DB constraint, both)? | ACC-01, CON-06 |
| Q-06 | Must AI-extracted transactions always require human confirmation before posting, or is auto-post allowed above a confidence threshold? If auto-post, define threshold and liability. | ACC-13, DEC-15, ASM-13 |
| Q-07 | Product liability boundary: does the system compute tax only, prepare returns, or file returns? | TAX-10, DEC-12 |
| Q-08 | Which GST returns (GSTR-1, 2B, 3B) are in scope for Phase 1, if any? | TAX-09 |

### High priority — must answer before architecture

| # | Question | Resolves |
|---|----------|----------|
| Q-09 | `Party` model: one entity with type flag, or separate Customer and Vendor entities? | AMB-02, DEC-03 |
| Q-10 | Roles and permissions: what roles exist and what can each role do (post, approve, view, admin, export)? | AMB-04, DEC-05, SEC-04 |
| Q-11 | Posted journal entry correction model: immutable + reversal entry, or editable with audit trail? | ACC-02 |
| Q-12 | Financial year and period locking rules (Indian April–March)? | ACC-03 |
| Q-13 | Accrual vs cash basis — which is supported in Phase 1? | ACC-11 |
| Q-14 | Tax rule version audit: store FK to `TaxRuleVersion`, immutable computation snapshot, or both? | AMB-01, DEC-06 |
| Q-15 | Storage for pilot: Cloudflare R2, host bundled storage, or MinIO? (Line 75 requires versioned object storage.) | CON-03, DEC-08 |
| Q-16 | GSP vendor: MasterGST or Masters India for Phase 1? | AMB-07, DEC-07 |
| Q-17 | Multi-tenancy enforcement: application-layer org scoping, Postgres RLS, or both? | TEC-04, SEC-14 |
| Q-18 | Define the report set referenced on line 97. | STR-07 |
| Q-19 | Define search requirements referenced on line 112. | STR-08, CON-07 |
| Q-20 | Duplicate invoice and duplicate payment detection rules? | ACC-06, ACC-07 |

### Medium priority — must answer before implementation

| # | Question | Resolves |
|---|----------|----------|
| Q-21 | OCR fallback activation criteria (when does Tesseract run vs Claude)? | AMB-06, DEC-14 |
| Q-22 | Invoice model: single entity with purchase/sale type, or separate entities? | AMB-05, DEC-13 |
| Q-23 | Polymorphic vs typed FKs for Anomaly, ApprovalRequest, AuditLogEntry? | AMB-03, DEC-04 |
| Q-24 | Partial payment, over-payment, and credit note application rules? | ACC-08, ACC-09 |
| Q-25 | Chart of accounts: seed standard Indian COA, blank slate, or import? | ACC-10 |
| Q-26 | Currency: INR-only for Phase 1? | ACC-04, ASM-07 |
| Q-27 | Rounding rules for line items, tax, and totals? | ACC-05 |
| Q-28 | Email provider: Resend or SendGrid? | AMB-08, DEC-09 |
| Q-29 | Hosting provider: Railway or Render? | AMB-09, DEC-10 |
| Q-30 | Dashboard auth approach: self-hosted JWT, OSS toolkit, or managed provider? | AMB-10 |
| Q-31 | Data residency and DPDP Act compliance requirements? | TAX-13, TAX-14, TEC-07 |
| Q-32 | Document and financial record retention periods? | TAX-12 |
| Q-33 | Pilot scale targets (orgs, invoices/day, users)? | AMB-11, ASM-09 |
| Q-34 | Should `EInvoice` entity exist in Phase 1 schema before provider integration? | CON-04 |
| Q-35 | Can one document map to multiple transactions, or is it strictly 1:N document→transaction? | AMB-11 |
| Q-36 | Journal entry idempotency: separate from job idempotency keys? | ACC-14 |

### Low priority — can defer to tech design if flagged

| # | Question | Resolves |
|---|----------|----------|
| Q-37 | Supply the referenced "baseline" document or remove baseline references from PRD. | STR-06 |
| Q-38 | API versioning strategy? | TEC-05 |
| Q-39 | CI/CD and testing requirements? | TEC-10 |
| Q-40 | WhatsApp template message strategy for outbound confirmations? | DEP-02 |

---

## Freeze Gate Checklist

Use this checklist before declaring PRD.md frozen. All Blocker items must be **Yes** before proceeding to Architecture (Stage 2).

| Gate criterion | Status | Notes |
|----------------|--------|-------|
| Complete PRD document available (not a fragment) | **FAIL** | STR-01 |
| Product vision and scope defined | **FAIL** | Coverage: Product definition |
| Phase definitions documented | **FAIL** | STR-05 |
| Functional requirements for Phase 1 MVP | **FAIL** | Coverage: all functional domains |
| Non-functional requirements (security, performance, backup) | **FAIL** | Coverage: NFR |
| Contradictions resolved (especially CON-01, CON-05) | **FAIL** | See Contradictions |
| Blocker questions (Q-01 through Q-08) answered | **FAIL** | See Questions |
| Accounting invariants stated as requirements | **FAIL** | ACC-01 |
| Tax/compliance liability boundary defined | **FAIL** | TAX-10 |
| Authentication model defined for Phase 1 | **FAIL** | SEC-01 |
| External dependencies identified and acceptable | **PARTIAL** | DEP-01–DEP-12 listed; procurement not confirmed |
| Edge cases reviewed and accepted or deferred explicitly | **FAIL** | Missing Edge Cases section |
| Stakeholder sign-off on Questions / Decisions Required | **FAIL** | Pending human review |

**Overall freeze status: NOT READY.**

---

## Appendix: PRD content inventory

For traceability, the complete section list present in PRD.md:

| Lines | Section |
|-------|---------|
| 1 | Title |
| 3–7 | Background Processing |
| 11 | Integration Architecture (inline table) |
| 15–18 | Database Model |
| 23–115 | Technology Selection and Cost Strategy |
| 25–33 | Backend (FastAPI) |
| 35–43 | Database (PostgreSQL) |
| 45–53 | AI / Document Understanding (Claude) |
| 55–62 | OCR fallback (Tesseract) |
| 64–71 | Background Jobs / Queue |
| 73–78 | Storage |
| 80–86 | Email |
| 88–93 | Hosting |
| 95–98 | Reporting |
| 100–103 | Authentication (Phase 2+) |
| 105–108 | Monitoring / Observability |
| 110–113 | Search |
| 115 | Messaging (WhatsApp) |

**Total substantive requirements sections: 4** (Background Processing, Integration Architecture, Database Model, Technology Selection). Everything else a complete PRD would contain is absent.
