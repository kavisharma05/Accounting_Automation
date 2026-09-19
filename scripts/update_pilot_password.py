#!/usr/bin/env python3
"""Update an existing pilot user's password (uses DATABASE_URL from env).

Usage (local .env):
  python scripts/update_pilot_password.py --email admin@pilot.local --password 'NewSecurePass123!'

Usage (Railway production DB):
  railway link --service Accounting_Automation
  railway run python scripts/update_pilot_password.py --email admin@pilot.local --password 'NewSecurePass123!'
"""

from __future__ import annotations

import argparse
import sys

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.entities import User


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    args = parser.parse_args()
    if len(args.password) < 12:
        print("Use a password of at least 12 characters.", file=sys.stderr)
        return 1

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == args.email).first()
        if not user:
            print(f"No user with email {args.email}", file=sys.stderr)
            return 1
        user.password_hash = hash_password(args.password)
        db.commit()
        print(f"Password updated for {args.email}")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
