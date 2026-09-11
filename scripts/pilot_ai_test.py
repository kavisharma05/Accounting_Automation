#!/usr/bin/env python3
"""End-to-end pilot test with a real invoice image (NVIDIA / Claude / etc.).

Usage:
  python scripts/pilot_ai_test.py --invoice path/to/invoice.jpg
  python scripts/pilot_ai_test.py --invoice invoice.jpg --base-url https://accountingautomation-production.up.railway.app
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import sys
import uuid
from pathlib import Path

import httpx

MOCK_TOTAL = "59000.00"


def main() -> int:
    parser = argparse.ArgumentParser(description="Test document AI extraction on production/staging")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--invoice", required=True, help="Path to invoice image (jpg/png/webp)")
    parser.add_argument("--timeout", type=float, default=180.0, help="HTTP timeout seconds")
    args = parser.parse_args()

    invoice_path = Path(args.invoice)
    if not invoice_path.is_file():
        print(f"Invoice file not found: {invoice_path}", file=sys.stderr)
        return 1

    mime, _ = mimetypes.guess_type(invoice_path.name)
    mime = mime or "image/jpeg"
    content = invoice_path.read_bytes()
    base = args.base_url.rstrip("/")

    with httpx.Client(timeout=args.timeout) as client:
        print("1. Health check...")
        r = client.get(f"{base}/api/v1/health")
        r.raise_for_status()
        print("   OK")

        print("2. Create organization...")
        r = client.post(
            f"{base}/api/v1/organizations",
            json={"name": "AI Pilot Test Org", "gstin": "29AABCU9603R1ZM"},
        )
        r.raise_for_status()
        org_id = r.json()["id"]
        print(f"   org_id={org_id}")

        print("3. Upload invoice...")
        r = client.post(
            f"{base}/api/v1/organizations/{org_id}/documents/upload",
            files={"file": (invoice_path.name, content, mime)},
        )
        r.raise_for_status()
        doc_id = r.json()["document_id"]
        print(f"   document_id={doc_id}")

        print("4. Extract with document AI (may take 1-3 min)...")
        r = client.post(f"{base}/api/v1/organizations/{org_id}/documents/{doc_id}/extract")
        if r.status_code >= 400:
            print(f"   FAILED ({r.status_code}): {r.text[:800]}", file=sys.stderr)
            return 1
        extraction = r.json()["data"]
        print("   Extraction:")
        print(json.dumps(extraction, indent=2))

        total = str(extraction.get("total", ""))
        if total == MOCK_TOTAL and extraction.get("vendor_name") == "Mock Vendor Pvt Ltd":
            print("\nWARNING: Result looks like mock data (59000 / Mock Vendor).", file=sys.stderr)
            print("Check DOCUMENT_PROVIDER and DOCUMENT_AI_API_KEY on API + worker.", file=sys.stderr)

        print("5. Propose invoice...")
        r = client.post(
            f"{base}/api/v1/organizations/{org_id}/documents/{doc_id}/propose-invoice",
        )
        r.raise_for_status()
        inv = r.json()
        print(f"   invoice_id={inv['invoice_id']} total={inv['total']} status={inv['status']}")

        print("6. Confirm and post to ledger...")
        r = client.post(f"{base}/api/v1/organizations/{org_id}/invoices/confirm-pending")
        r.raise_for_status()
        posted = r.json()
        print(f"   journal_entry_id={posted['journal_entry_id']}")

        print("7. Export ledger...")
        r = client.get(
            f"{base}/api/v1/organizations/{org_id}/reports/ledger.xlsx",
            headers={"X-Organization-Id": org_id},
        )
        r.raise_for_status()
        out = Path(f"ledger-{org_id[:8]}.xlsx")
        out.write_bytes(r.content)
        print(f"   saved {out} ({len(r.content)} bytes)")

        print("\nPilot AI test PASSED")
        print(json.dumps({"org_id": org_id, "invoice_id": inv["invoice_id"], "total": inv["total"]}, indent=2))
        return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except httpx.HTTPStatusError as e:
        print(f"\nHTTP error: {e.response.status_code} {e.response.text[:800]}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\nPilot AI test FAILED: {e}", file=sys.stderr)
        sys.exit(1)
