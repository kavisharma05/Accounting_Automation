#!/usr/bin/env python3
"""Initialize database schema via Alembic migrations.

Usage:
  python scripts/init_db.py              # alembic upgrade head
  python scripts/init_db.py --create-all # dev fallback (create_all)
"""

import argparse
import subprocess
import sys


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--create-all",
        action="store_true",
        help="Use Base.metadata.create_all instead of Alembic (dev only)",
    )
    args = parser.parse_args()

    if args.create_all:
        import app.models.entities  # noqa: F401
        from app.core.database import Base, engine

        Base.metadata.create_all(bind=engine)
        print("Database schema created (create_all).")
        return

    result = subprocess.run(["alembic", "upgrade", "head"], check=False)
    if result.returncode != 0:
        sys.exit(result.returncode)
    print("Database migrated to head.")


if __name__ == "__main__":
    main()
