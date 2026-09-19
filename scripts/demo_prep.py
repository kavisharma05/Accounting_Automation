#!/usr/bin/env python3
"""Prepare the logged-in pilot org for a screen-recorded demo.

Uploads a vendor bill into the existing dashboard org (not a throwaway org),
proposes + posts it, then writes a matching bank CSV for the reconcile step.

Usage:
  python scripts/demo_prep.py --invoice scripts/real-gst-invoice.jpg
  python scripts/demo_prep.py --base-url https://accountingautomation-production.up.railway.app \\
      --email admin@pilot.local --password 'YourPassword'
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import sys
from datetime import date
from pathlib import Path

import httpx


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed the pilot org for a demo recording")
    parser.add_argument(
        "--base-url",
        default="https://accountingautomation-production.up.railway.app",
    )
    parser.add_argument("--email", default="admin@pilot.local")
    parser.add_argument("--password", default="pilot-admin-change-me")
    parser.add_argument(
        "--invoice",
        default="scripts/sample-invoice.jpg",
        help="Vendor bill image/PDF to upload",
    )
    parser.add_argument(
        "--skip-confirm",
        action="store_true",
        help="Leave the bill pending so Confirm & post is clicked on camera",
    )
    parser.add_argument("--timeout", type=float, default=180.0)
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
        print("1. Login...")
        r = client.post(
            f"{base}/api/v1/auth/login",
            json={"email": args.email, "password": args.password},
        )
        if r.status_code != 200:
            print(f"   Login failed ({r.status_code}): {r.text[:400]}", file=sys.stderr)
            return 1
        token = r.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        print("2. Load org...")
        r = client.get(f"{base}/api/v1/me", headers=headers)
        r.raise_for_status()
        me = r.json()
        org_id = me["organization_id"]
        print(f"   {me['organization_name']} ({org_id})")

        print("3. Upload vendor bill...")
        r = client.post(
            f"{base}/api/v1/organizations/{org_id}/documents/upload",
            headers=headers,
            files={"file": (invoice_path.name, content, mime)},
        )
        r.raise_for_status()
        doc_id = r.json()["document_id"]
        print(f"   document_id={doc_id}")

        print("4. Extract + propose invoice (may take 1-3 min if AI is live)...")
        r = client.post(
            f"{base}/api/v1/organizations/{org_id}/documents/{doc_id}/propose-invoice",
            headers=headers,
        )
        if r.status_code >= 400:
            print(f"   FAILED ({r.status_code}): {r.text[:800]}", file=sys.stderr)
            return 1
        inv = r.json()
        print(
            f"   {inv['invoice_number']} total={inv['total']} status={inv['status']}"
        )

        journal_id = None
        if not args.skip_confirm:
            print("5. Confirm and post...")
            r = client.post(
                f"{base}/api/v1/organizations/{org_id}/invoices/confirm-pending",
                headers=headers,
            )
            if r.status_code >= 400:
                print(f"   FAILED ({r.status_code}): {r.text[:800]}", file=sys.stderr)
                return 1
            posted = r.json()
            journal_id = posted.get("journal_entry_id")
            print(f"   journal_entry_id={journal_id}")
        else:
            print("5. Left pending — confirm on camera from Invoices → Confirm & post")

        today = date.today().isoformat()
        payment_amount = inv["total"]
        csv_path = Path("scripts/demo-bank-statement.csv")
        csv_path.write_text(
            "date,description,amount,reference\n"
            f"{today},Vendor payment UTRDEMO001,-{payment_amount},UTRDEMO001\n",
            encoding="utf-8",
        )
        print(f"6. Wrote {csv_path}")

        cheat = {
            "dashboard": base,
            "login_email": args.email,
            "org": me["organization_name"],
            "purchase_invoice": inv["invoice_number"],
            "purchase_total": inv["total"],
            "purchase_status": "posted" if journal_id else inv["status"],
            "sales_invoice": "SI-DEMO-001",
            "sales_taxable": "10000",
            "sales_tax": "1800",
            "payment_amount": payment_amount,
            "payment_date": today,
            "payment_reference": "UTRDEMO001",
            "bank_csv": str(csv_path),
            "credit_note": "CN-DEMO-001",
            "credit_note_taxable": "1000",
            "credit_note_tax": "180",
        }
        print("\n=== DEMO CHEAT SHEET — keep this beside the recording ===")
        print(json.dumps(cheat, indent=2))
        print("\nDemo prep PASSED")
        return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except httpx.HTTPStatusError as e:
        print(f"\nHTTP error: {e.response.status_code} {e.response.text[:800]}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\nDemo prep FAILED: {e}", file=sys.stderr)
        sys.exit(1)
