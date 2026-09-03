#!/usr/bin/env python3
"""Seed a pilot organization with COA, accounts, phone mapping, and admin user.

Usage:
  python scripts/seed_pilot_org.py
  python scripts/seed_pilot_org.py --phone +919876543210 --name "Acme Pvt Ltd"
"""

import argparse
import json
from datetime import UTC, datetime

import app.models.entities  # noqa: F401
from app.core.database import SessionLocal, engine, Base
from app.core.security import hash_password
from app.domain.organizations.coa_seed import seed_chart_of_accounts
from app.domain.organizations.pilot_config import configure_pilot_accounts
from app.models.entities import (
    MembershipRole,
    Organization,
    OrganizationMembership,
    PhoneOrgMapping,
    User,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", default="Pilot Organization")
    parser.add_argument("--gstin", default="29AABCU9603R1ZM")
    parser.add_argument("--phone", default="+919876543210")
    parser.add_argument("--email", default="admin@pilot.local")
    parser.add_argument("--password", default="pilot-admin-change-me")
    args = parser.parse_args()

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        org = Organization(name=args.name, gstin=args.gstin)
        db.add(org)
        db.flush()
        seed_chart_of_accounts(db, org.id)
        configure_pilot_accounts(db, org.id, auto_from_coa=True)

        user = User(email=args.email, password_hash=hash_password(args.password))
        db.add(user)
        db.flush()
        db.add(
            OrganizationMembership(
                organization_id=org.id,
                user_id=user.id,
                role=MembershipRole.owner,
            )
        )
        db.add(
            PhoneOrgMapping(
                organization_id=org.id,
                phone_e164=args.phone,
                verified_at=datetime.now(UTC),
            )
        )
        db.commit()
        db.refresh(org)

        print(json.dumps({
            "organization_id": str(org.id),
            "name": org.name,
            "gstin": org.gstin,
            "phone": args.phone,
            "admin_email": args.email,
            "default_expense_account_id": str(org.default_expense_account_id),
            "default_payable_account_id": str(org.default_payable_account_id),
            "default_input_tax_account_id": str(org.default_input_tax_account_id),
        }, indent=2))
    finally:
        db.close()


if __name__ == "__main__":
    main()
