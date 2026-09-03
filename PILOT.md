# Pilot Runbook

**Stage:** 16 of 18

## Objective

Validate real workflows with 3–5 Indian SMBs before broad launch. Collect failure cases the PRD cannot predict.

## Prerequisites

- [DEPLOYMENT.md](DEPLOYMENT.md) staging environment deployed
- WhatsApp Business account verified
- Anthropic API key with budget cap
- GSP sandbox credentials (MasterGST/Masters India)
- CA partner for report review

## Pilot scope (Phase 1)

| In scope | Out of scope |
|----------|--------------|
| Purchase invoice via WhatsApp photo | E-invoice NIC filing |
| AI extraction + human confirmation | GSTR return filing |
| Double-entry posting | Multi-currency |
| Basic GST on invoice | Bank reconciliation automation |
| Ledger Excel/PDF export | Dashboard UI |

## Onboarding checklist per organization

1. Create organization + GSTIN in API
2. Seed chart of accounts (expense, payables, input GST)
3. Register WhatsApp phone → org mapping
4. Configure default account IDs for webhook
5. Send test invoice image
6. Confirm extraction summary via WhatsApp YES
7. Verify journal entry: debits = credits
8. Export ledger for CA review

## Metrics to collect

- Extraction field accuracy (vendor, total, GSTIN, date)
- Confirmation rate vs rejection rate
- Time from upload to post
- Job failure / dead-letter count
- User confusion points (support log)

## Human verification

Every posted entry in pilot period must be reviewed by bookkeeper or CA weekly.

## Exit criteria

- 50+ real invoices processed with <5% posting corrections
- Zero cross-tenant data incidents
- Zero duplicate posts from retries
- Dead-letter queue empty or triaged within 24h

## Failure case log

Maintain spreadsheet: document image, extraction JSON, user action, root cause, fix applied.
