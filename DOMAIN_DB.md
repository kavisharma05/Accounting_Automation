# Database & Domain Design

**Stage:** 4 of 18

## Conventions

- PK: UUID (`gen_random_uuid()`)
- Timestamps: `created_at`, `updated_at` (UTC)
- Soft delete: `deleted_at` nullable on business entities
- Tenant: `organization_id` NOT NULL on all tenant tables; indexed
- Money: `NUMERIC(18,2)` in INR **(IMP-DEFAULT)**
- Audit: `created_by_id`, `updated_by_id` where applicable

## Entity definitions

### Organization & auth

**organizations**
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| name | VARCHAR(255) | |
| gstin | VARCHAR(15) NULL | |
| financial_year_start_month | INT DEFAULT 4 | April **(IMP-DEFAULT)** |
| created_at, updated_at, deleted_at | TIMESTAMPTZ | |

**users**
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| email | VARCHAR(255) UNIQUE | |
| phone | VARCHAR(20) UNIQUE NULL | WhatsApp binding |
| password_hash | VARCHAR NULL | API auth |
| created_at, updated_at | TIMESTAMPTZ | |

**organization_memberships**
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| organization_id | FK organizations | |
| user_id | FK users | |
| role | ENUM owner, accountant, viewer, admin | **(IMP-DEFAULT)** |
| UNIQUE(organization_id, user_id) | | |

**phone_org_mappings** (WhatsApp auth **IMP-DEFAULT**)
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| organization_id | FK | |
| phone_e164 | VARCHAR(20) | |
| verified_at | TIMESTAMPTZ | |
| UNIQUE(phone_e164) | | |

### Chart of accounts

**chart_of_accounts**
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| organization_id | FK | |
| code | VARCHAR(32) | |
| name | VARCHAR(255) | |
| account_type | ENUM asset, liability, equity, revenue, expense | |
| is_active | BOOLEAN | |
| UNIQUE(organization_id, code) | | |

### Ledger (accounting engine core)

**journal_entries**
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| organization_id | FK | |
| entry_number | VARCHAR | sequential per org |
| entry_date | DATE | |
| description | TEXT | |
| status | ENUM draft, posted, reversed | |
| source_type | VARCHAR | invoice, expense, payment, manual, reversal |
| source_id | UUID NULL | |
| idempotency_key | VARCHAR NULL | |
| reversed_by_id | FK journal_entries NULL | |
| posted_at | TIMESTAMPTZ NULL | |
| posted_by_id | FK users NULL | |
| UNIQUE(organization_id, idempotency_key) WHERE idempotency_key IS NOT NULL | | |
| UNIQUE(organization_id, source_type, source_id) WHERE source_id IS NOT NULL | | |

**journal_entry_lines**
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| journal_entry_id | FK | ON DELETE RESTRICT |
| chart_of_account_id | FK | |
| debit | NUMERIC(18,2) DEFAULT 0 | |
| credit | NUMERIC(18,2) DEFAULT 0 | |
| description | TEXT NULL | |
| CHECK (debit >= 0 AND credit >= 0) | | |
| CHECK (NOT (debit > 0 AND credit > 0)) | | |

**Constraint (application + DB trigger IMP-DEFAULT):** on post, `SUM(debit) = SUM(credit)` and at least 2 lines.

### Parties & transactions

**parties** — unified with type flag **(IMP-DEFAULT Q-09)**
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| organization_id | FK | |
| party_type | ENUM customer, vendor, both | |
| name | VARCHAR(255) | |
| gstin | VARCHAR(15) NULL | |

**invoices**
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| organization_id | FK | |
| party_id | FK parties | |
| invoice_type | ENUM purchase, sales | |
| invoice_number | VARCHAR | |
| invoice_date | DATE | |
| subtotal, tax_total, total | NUMERIC | |
| status | ENUM draft, pending_approval, posted, cancelled | |
| journal_entry_id | FK NULL | set on post |
| tax_rule_version_id | FK NULL | snapshot ref **(IMP-DEFAULT)** |
| tax_computation_snapshot | JSONB NULL | immutable audit **(IMP-DEFAULT)** |

**invoice_line_items**, **expenses**, **credit_notes**, **debit_notes** — analogous pattern.

**payments**, **payment_applications** — many-to-many link.

### Documents & AI

**documents**
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| organization_id | FK | |
| storage_key | VARCHAR | |
| mime_type | VARCHAR | |
| sha256 | VARCHAR(64) | dedup |
| uploaded_by_id | FK NULL | |

**ai_extraction_records**
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| document_id | FK | |
| provider | VARCHAR | |
| model | VARCHAR | |
| extracted_data | JSONB | |
| confidence | NUMERIC(5,4) NULL | |
| raw_response_ref | VARCHAR NULL | |
| created_at | TIMESTAMPTZ | |

**document_transaction_links** — M:N document ↔ invoice/expense.

### Jobs, audit, approvals

**background_jobs** — state, idempotency_key, dead_letter_at, payload JSONB.

**audit_log_entries** — typed FK **(IMP-DEFAULT)**: entity_type + entity_id.

**approval_requests** — pending confirmation before post.

**anomalies** — flagged issues on extractions/transactions.

### Tax & compliance

**tax_rule_versions** — effective_from, rules JSONB (GST rates slabs).

**eway_bills**, **einvoices** — link to invoice, external refs.

## Tenant isolation

All repository queries: `WHERE organization_id = :ctx_org_id`.

Index every `(organization_id, ...)` lookup column.

## Soft deletion

`deleted_at IS NULL` filter in repositories; posted journal entries never soft-deleted.

## Indexes (critical)

- `journal_entries(organization_id, entry_date)`
- `journal_entry_lines(journal_entry_id)`
- `invoices(organization_id, invoice_number, party_id)` — duplicate detection
- `background_jobs(organization_id, idempotency_key)` UNIQUE
- `documents(organization_id, sha256)`
