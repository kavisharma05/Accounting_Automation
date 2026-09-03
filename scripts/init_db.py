#!/usr/bin/env python3
"""Initialize database schema. Usage: python scripts/init_db.py"""

import app.models.entities  # noqa: F401
from app.core.database import Base, engine

if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    print("Database schema created.")
