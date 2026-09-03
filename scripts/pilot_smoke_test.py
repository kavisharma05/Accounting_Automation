#!/usr/bin/env python3
"""End-to-end pilot smoke test (no WhatsApp required).

Usage:
  python scripts/pilot_smoke_test.py [--base-url http://localhost:8000]
"""

import argparse
import json
import sys
from io import BytesIO

import httpx


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:8000")
    args = parser.parse_args()
    base = args.base_url.rstrip("/")

    with httpx.Client(timeout=30) as client:
        # Health
        r = client.get(f"{base}/api/v1/health")
        r.raise_for_status()
        assert r.json()["status"] == "ok"
        print("✓ health")

        # Create org (COA + pilot accounts auto-configured)
        r = client.post(
            f"{base}/api/v1/organizations",
            json={"name": "Smoke Test Org", "gstin": "29AABCU9603R1ZM"},
        )
        r.raise_for_status()
        org_id = r.json()["id"]
        print(f"✓ organization {org_id}")

        # Pilot config
        r = client.get(f"{base}/api/v1/organizations/{org_id}/pilot-config")
        r.raise_for_status()
        cfg = r.json()
        assert cfg["default_expense_account_id"]
        print("✓ pilot config")

        # Phone mapping
        r = client.post(
            f"{base}/api/v1/organizations/{org_id}/phone-mappings",
            json={"phone_e164": "+919999990001"},
        )
        r.raise_for_status()
        print("✓ phone mapping")

        # Upload mock invoice
        r = client.post(
            f"{base}/api/v1/organizations/{org_id}/documents/upload",
            files={"file": ("invoice.jpg", BytesIO(b"mock invoice bytes"), "image/jpeg")},
        )
        r.raise_for_status()
        doc_id = r.json()["document_id"]
        print(f"✓ document upload {doc_id}")

        # Propose invoice from extraction
        r = client.post(
            f"{base}/api/v1/organizations/{org_id}/documents/{doc_id}/propose-invoice",
        )
        r.raise_for_status()
        inv = r.json()
        print(f"✓ invoice proposed {inv['invoice_id']} total={inv['total']}")

        # Confirm pending
        r = client.post(f"{base}/api/v1/organizations/{org_id}/invoices/confirm-pending")
        r.raise_for_status()
        posted = r.json()
        assert posted["journal_entry_id"]
        print(f"✓ posted journal entry {posted['journal_entry_id']}")

        # Export ledger
        r = client.get(
            f"{base}/api/v1/organizations/{org_id}/reports/ledger.xlsx",
            headers={"X-Organization-Id": org_id},
        )
        r.raise_for_status()
        assert len(r.content) > 100
        print("✓ ledger export")

        print("\nPilot smoke test PASSED")
        print(json.dumps({"org_id": org_id, "invoice_id": inv["invoice_id"]}, indent=2))
        return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"\nPilot smoke test FAILED: {e}", file=sys.stderr)
        sys.exit(1)
