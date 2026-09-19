#!/usr/bin/env python3
"""Smoke-check a deployed API (health, readiness, optional auth login).

Usage:
  python scripts/verify_production.py
  python scripts/verify_production.py --base-url https://accountingautomation-production.up.railway.app
  python scripts/verify_production.py --login admin@pilot.local --password 'your-password'
"""

from __future__ import annotations

import argparse
import sys

import httpx


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify production/staging deployment")
    parser.add_argument(
        "--base-url",
        default="https://accountingautomation-production.up.railway.app",
    )
    parser.add_argument("--login", help="Pilot admin email for JWT check")
    parser.add_argument("--password", help="Pilot admin password")
    args = parser.parse_args()
    base = args.base_url.rstrip("/")

    with httpx.Client(timeout=30.0) as client:
        for path, label in (
            ("/api/v1/health", "health"),
            ("/api/v1/health/live", "liveness"),
            ("/api/v1/health/ready", "readiness"),
        ):
            r = client.get(f"{base}{path}")
            ok = r.status_code == 200
            print(f"{'OK' if ok else 'FAIL'} {label}: {r.status_code}")
            if not ok:
                print(r.text[:500], file=sys.stderr)
                return 1

        if args.login and args.password:
            r = client.post(
                f"{base}/api/v1/auth/login",
                json={"email": args.login, "password": args.password},
            )
            if r.status_code != 200:
                print(f"FAIL login: {r.status_code} {r.text[:300]}", file=sys.stderr)
                return 1
            token = r.json().get("access_token")
            print(f"OK login: token received ({len(token or '')} chars)")

    print("\nProduction verify PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
