# Pilot Runbook

**Stage:** 16 — Active

## Quick start (local)

```bash
# 1. Start stack
docker compose up --build -d

# 2. Seed pilot org (optional — or create via API)
docker compose --profile tools run --rm seed

# 3. Run smoke test (upload → extract → confirm → ledger)
python scripts/pilot_smoke_test.py --base-url http://localhost:8000
```

API docs: http://localhost:8000/docs

## Onboarding checklist per organization

### Via API (recommended)

```bash
BASE=http://localhost:8000

# Create org — auto-seeds COA + default accounts (5000/2000/1400)
curl -X POST $BASE/api/v1/organizations \
  -H 'Content-Type: application/json' \
  -d '{"name":"Acme Pvt Ltd","gstin":"29AABCU9603R1ZM"}'

# Register WhatsApp phone
curl -X POST $BASE/api/v1/organizations/{ORG_ID}/phone-mappings \
  -H 'Content-Type: application/json' \
  -d '{"phone_e164":"+919876543210"}'

# Verify pilot config
curl $BASE/api/v1/organizations/{ORG_ID}/pilot-config
```

### Test without WhatsApp

```bash
# Upload invoice image
curl -X POST $BASE/api/v1/organizations/{ORG_ID}/documents/upload \
  -F "file=@invoice.jpg"

# Propose invoice from AI extraction
curl -X POST $BASE/api/v1/organizations/{ORG_ID}/documents/{DOC_ID}/propose-invoice

# Confirm and post (simulates WhatsApp YES)
curl -X POST $BASE/api/v1/organizations/{ORG_ID}/invoices/confirm-pending \
  -H "X-Organization-Id: {ORG_ID}"

# Export ledger for CA
curl -o ledger.xlsx $BASE/api/v1/organizations/{ORG_ID}/reports/ledger.xlsx \
  -H "X-Organization-Id: {ORG_ID}"
```

## Production pilot setup

1. Copy [.env.example](.env.example) → `.env`
2. Set `MESSAGING_PROVIDER=whatsapp`, `DOCUMENT_PROVIDER=claude`
3. Configure Meta webhook: `GET/POST https://your-host/webhooks/whatsapp`
4. Set `WHATSAPP_VERIFY_TOKEN`, `WHATSAPP_APP_SECRET`, tokens
5. Deploy to Railway/Render with Postgres + Redis add-ons
6. Run `python scripts/init_db.py` on first deploy

## Pilot scope (Phase 1)

| In scope | Out of scope |
|----------|--------------|
| Purchase invoice via WhatsApp or API upload | E-invoice NIC filing |
| AI extraction + human confirmation | GSTR return filing |
| Double-entry posting | Multi-currency |
| Basic GST on invoice | Bank reconciliation |
| Ledger Excel/PDF export | Dashboard UI |

## Exit criteria

- 50+ real invoices with <5% posting corrections
- Zero cross-tenant incidents
- Zero duplicate posts from retries
- Dead-letter queue triaged within 24h

## Failure case log

Track: document image, extraction JSON, user action, root cause, fix.
