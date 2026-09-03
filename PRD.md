# Product Requirements Document (PRD)

> **Ratified baseline:** This file is the original technology fragment. Complete requirements are in [PRD_SUPPLEMENT.md](PRD_SUPPLEMENT.md) with decisions in [PRD_DECISIONS.md](PRD_DECISIONS.md). **Status: FROZEN** (2026-09-03).

### Background Processing

**Jobs requiring async execution:** AI/OCR document processing, report generation, email dispatch, bank statement processing, reconciliation runs, notification dispatch, e-way bill generation requests, e-invoice generation requests.

**Requirements:** each job has a tracked state (`QUEUED`/`RUNNING`/`SUCCEEDED`/`FAILED`/`RETRYING`), automatic retry with backoff for transient failures, idempotency keys so a retried or duplicated job cannot double-post a financial effect, and a dead-letter path for jobs that exhaust retries (surfaced to an admin, not silently dropped).  Free/open-source queue technology is evaluated ahead of paid infrastructure — see [Technology Selection and Cost Strategy](#technology-selection-and-cost-strategy).

---

### Integration Architecture  The core accounting/tax domain must have **zero direct dependency** on any vendor SDK. Every external system sits behind an internal interface:  | Interface | Default Phase 1 implementation | Purpose | |---|---|---| | `MessagingProvider` | WhatsApp Cloud API | Inbound/outbound WhatsApp messages | | `DocumentUnderstandingProvider` | Claude Sonnet (vision) | Extraction, classification | | `OcrFallbackProvider` | Tesseract | Fallback OCR | | `EmailProvider` | Resend or SendGrid | Transactional email | | `StorageProvider` | Managed object storage (see evaluation) | Document storage | | `GspProvider` | MasterGST/Masters India sandbox | E-way bill | | `EInvoiceProvider` | Not connected in Phase 1 (interface defined, unimplemented) | E-invoicing (Phase 3+) | | `HostingTarget` | Railway/Render (container) | Deployment |  Swapping any one of these must not require touching accounting/tax domain code — only the adapter implementing that interface.

---

### Database Model  This PRD defines the **conceptual entity set**, not a schema/migration (explicitly out of scope for this document per the final instruction).

**Core entities:** `Organization`, `User`, `OrganizationMembership` (user↔org with role), `ChartOfAccount`, `JournalEntry`, `JournalEntryLine`, `Document`, `Invoice` (purchase/sale), `InvoiceLineItem`, `CreditNote`, `DebitNote`, `Expense`, `Party` (customer/vendor, possibly split into two entities or one with a type flag), `Payment`, `PaymentApplication` (payment↔invoice link, supports many-to-many), `BankAccount`, `BankStatementTransaction`, `ReconciliationMatch`, `TaxRuleVersion` (GST/TDS config), `EWayBill`, `EInvoice`, `Anomaly`, `ApprovalRequest`, `AuditLogEntry`, `Notification`, `ComplianceCalendarEntry`, `AIExtractionRecord` (provenance).

**Key relationships:** every tenant-owned entity → `Organization`. `Invoice`/`Expense`/`CreditNote`/`DebitNote` → one or more `Document` (source) and, once posted, exactly one `JournalEntry`. `JournalEntry` → two or more `JournalEntryLine`, each → one `ChartOfAccount`. `Payment` → `PaymentApplication` → `Invoice`(s). `EWayBill`/`EInvoice` → one `Invoice`. `Anomaly`/`ApprovalRequest`/`AuditLogEntry` → the entity they concern, polymorphically or via typed foreign keys (implementer's choice). `TaxRuleVersion` is not linked to individual transactions directly — it's looked up by the tax engine at computation time by effective date/category, and the *result* of that lookup (which rule version was applied) is recorded on the transaction for auditability.

---

### Technology Selection and Cost Strategy  Per the critical principle governing this PRD: **the baseline stack is a starting point, not a mandate.** Every major component is evaluated below on capability, reliability, maintainability, security, scalability, and cost — free/open-source is preferred *only* where it is genuinely fit for purpose.

#### Backend
| | Recommendation | Rationale | |---|---|---|
| Recommended | **Python / FastAPI** (baseline retained) | Async-native, strong typing via Pydantic (which doubles as the AI structured-output validation layer), fastest path to the same team building AI-integration code, reporting (pandas/openpyxl), and API in one language |
| Free/OSS | Yes | — |
| Pilot cost | $0 | — |
| Production cost | $0 (compute cost only, covered under Hosting) | — |
| Alternatives considered | Django (heavier, batteries-included ORM/admin — attractive for Phase 2+ dashboard admin needs, but a mid-project framework switch is costly); Node.js/NestJS (comparable capability, no strong reason to fragment from Python given AI/reporting tooling is Python-native) | |
| Why FastAPI wins | Lowest friction for the AI-heavy, schema-validated pipeline this product is built around; Django's admin-panel advantage is not decisive since a proper dashboard is being built anyway | |
| Replaceability | API domain boundaries (see [API Architecture](#api-architecture)) keep business logic decoupled from the web framework; a future migration is possible but not planned | |

#### Database
| | Recommendation | Rationale | |---|---|---|
| Recommended | **PostgreSQL** (baseline retained) | Strong relational integrity guarantees (critical for double-entry invariants), mature JSON support (for storing AI extraction payloads/config), full-text search sufficient for Phase 2–3 search needs, excellent free-tier managed options |
| Free/OSS | Yes (self-hostable); managed free tiers available (Supabase, Neon, Railway) | |
| Pilot cost | $0 | |
| Production cost | Usage-based, typically $10–50/mo at small-business multi-tenant scale on managed tiers; scales with data volume | |
| Alternatives considered | MySQL (comparable, weaker JSON/full-text ergonomics for this use case); MongoDB (poor fit — financial ledger data is fundamentally relational and needs transactional integrity that document databases handle less naturally) | |
| Why Postgres wins | Best fit for enforced debit=credit invariants (via constraints/transactions), mature ecosystem, avoids introducing a second database technology for search until proven necessary | |
| Replaceability | Data-access layer abstracted behind repository/service classes so schema/engine changes don't ripple into business logic | |

#### AI / Document Understanding
| | Recommendation | Rationale | |---|---|---|
| Recommended | **Claude Sonnet (vision-enabled), via Anthropic API** (baseline retained) | Single-call structured extraction + classification, strong reasoning on ambiguous/messy real-world invoices, no separate OCR pipeline to build/maintain |
| Free/OSS | No — usage-based paid API | |
| Pilot cost | Trivial at a handful of invoices/day (per baseline's own cost note); exact current pricing must be checked at docs.claude.com before go-live, not assumed from training data | |
| Production cost | Scales per-document; the one genuinely variable cost line in the whole stack | |
| Alternatives considered | GPT-4o/4.1-class vision (functionally comparable per baseline's own analysis — acceptable substitute, not a clear win); open-source local vision-LLMs (e.g., Qwen-VL, LLaVA-class models) — evaluated and **not recommended for Phase 1**: meaningfully weaker structured extraction reliability on messy real-world invoice photos as of current open-model quality, and self-hosting a vision model adds GPU infra cost/complexity that likely exceeds Claude's per-document API cost at pilot volume; dedicated invoice-OCR (Textract/Document AI/Docsumo/Nanonets) — slower to integrate in the timeline available, and still needs an LLM call on top for purchase/sale classification, per baseline's own analysis |
| Why Claude wins | This is a case where a paid technology is justified: document-understanding quality directly determines financial-record correctness, and open-source alternatives are not yet reliably competitive for this task. Revisit at each phase gate as open-source vision-LLMs mature | |
| Replaceability | Fully abstracted behind `DocumentUnderstandingProvider` (see [Integration Architecture](#integration-architecture)); switching providers is a config/adapter change, not a domain rewrite | |

#### OCR (fallback)
| | Recommendation | Rationale | |---|---|---|
| Recommended | **Tesseract** (baseline retained) for Phase 1; **evaluate PaddleOCR** as a Phase 2 upgrade | Tesseract is free, offline, and adequate purely as a backstop (not primary engine) per baseline design |
| Free/OSS | Yes, both options | |
| Pilot cost | $0 | |
| Production cost | $0 (self-hosted, compute already provisioned) | |
| Alternatives considered | EasyOCR (comparable OSS option); PaddleOCR (generally stronger on structured/tabular text than Tesseract, worth a Phase 2 evaluation once real failure-mode data exists from the pilot) | |
| Why Tesseract wins for now | It is a fallback, not the primary engine — optimizing it prematurely is not worth the effort before pilot data shows it's needed | |

#### Background Jobs / Queue
| | Recommendation | Rationale | |---|---|---|
| Recommended | **Celery + Redis** for Phase 2+ (not required for a literal Phase-1 pilot at a handful of invoices/day, where synchronous/simple async via FastAPI background tasks suffices); **RQ** as a simpler alternative if the team wants less operational surface than Celery | Redis-backed queues are mature, free/OSS, and well-documented; RQ trades some feature depth for much simpler ops |
| Free/OSS | Yes | |
| Pilot cost | $0 (Redis free tier via most managed providers, or self-hosted) | |
| Production cost | Low; Redis managed tiers are cheap at this scale | |
| Alternatives considered | Dramatiq (comparable, smaller ecosystem); cloud-managed queues (SQS, etc.) — unnecessary lock-in and cost at this scale | |
| Why Celery/RQ wins | Avoids introducing a heavier message-broker (Kafka, RabbitMQ) for a workload this PRD does not expect to need that scale for in the phases defined | |

#### Storage
| | Recommendation | Rationale | |---|---|---|
| Recommended | **S3-compatible object storage** (evaluate Cloudflare R2 for zero egress fees, or the hosting provider's bundled storage) behind `StorageProvider` | Documents are the audit backbone (Principle 2) — needs durable, versioned storage, not local disk, even in pilot | | Free/OSS-friendly | Free tiers widely available at pilot document volume | |
| Pilot cost | $0 | |
| Production cost | Usage-based, low at small-business document volume | |
| Alternatives considered | Local filesystem (rejected — not durable, not viable once hosting scales beyond a single instance); self-hosted MinIO (viable free/OSS alternative if the team prefers full control) | |

#### Email
| | Recommendation | Rationale | |---|---|---|
| Recommended | **Resend** (baseline option; SendGrid as equal alternative) | Reliable delivery + logging for the CA-facing report and notification emails, generous free tier |
| Free/OSS | No (but generous free tier) | |
| Pilot cost | $0 | |
| Production cost | Low, usage-based | |
| Alternatives considered | Raw SMTP (free but weaker deliverability/logging — a worse fit for CA-facing compliance email that must be reliably delivered) | |

#### Hosting
| | Recommendation | Rationale | |---|---|---|
| Recommended | **Railway or Render** (baseline retained) for Phase 1–2; re-evaluate at Phase 5 (production hardening) against a broader set (Fly.io, a cloud provider's managed container service) once real load/compliance requirements are known | Deploy-on-push simplicity, negligible pilot cost, no ops burden while the product is proving itself |
| Free/OSS | No, but low-cost | |
| Pilot cost | $0–low | |
| Production cost | Modest at small-business multi-tenant scale; revisit if scaling beyond what these platforms comfortably support | |

#### Reporting
| | Recommendation | Rationale | |---|---|---|
| Recommended | **pandas + openpyxl (Excel) + reportlab (PDF)** (baseline retained) | Free, mature, sufficient for the defined report set; no paid BI/reporting tool is justified at this scope | |
| Free/OSS | Yes | |

#### Authentication (dashboard, Phase 2+)
| | Recommendation | Rationale | |---|---|---|
| Recommended | Self-hosted auth using FastAPI-native JWT/session handling, or an open-source auth toolkit, for Phase 2; evaluate a managed provider with a strong free tier (e.g., one offering generous free MAUs) if team velocity benefits outweigh the lock-in | Avoid unnecessary paid auth infra before the dashboard's user volume justifies it | |
| Free/OSS | Self-hosted option: yes | |

#### Monitoring / Observability
| | Recommendation | Rationale | |---|---|---|
| Recommended | Structured logging (built-in) + an open-source-friendly error tracker with a free tier (e.g., Sentry's free tier) | Sufficient signal for pilot/early production without committing to paid APM before it's needed | |
| Free/OSS | Free tier acceptable at this scale | |

#### Search
| | Recommendation | Rationale | |---|---|---|
| Recommended | **PostgreSQL full-text search** through at least Phase 3 | Avoids standing up a dedicated search system (Elasticsearch/etc.) before data volume or query complexity justifies it; Postgres FTS is free and adequate for the defined [Search](#search) requirements at this scale | |
| Revisit | If search relevance/scale becomes a genuine bottleneck in later phases, evaluate a dedicated engine then — not preemptively | |

#### Messaging  WhatsApp Cloud API remains the primary target per baseline; kept behind `MessagingProvider` so a future channel (e.g., a native app) can be added without touching business logic, consistent with the baseline's own "only Layer 1 changes" architecture note.
