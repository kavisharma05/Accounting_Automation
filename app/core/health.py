"""Dependency readiness checks for load balancers."""

import logging
from datetime import UTC, datetime

from sqlalchemy import text

from app.core.config import settings

logger = logging.getLogger(__name__)


def check_database() -> tuple[bool, str]:
    try:
        from app.core.database import engine

        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True, "ok"
    except Exception as exc:
        logger.warning("Database health check failed: %s", exc)
        return False, str(exc)


def check_redis() -> tuple[bool, str]:
    try:
        import redis

        client = redis.from_url(settings.redis_url, socket_connect_timeout=2)
        client.ping()
        return True, "ok"
    except Exception as exc:
        logger.warning("Redis health check failed: %s", exc)
        return False, str(exc)


def readiness_status() -> dict:
    db_ok, db_msg = check_database()
    redis_ok, redis_msg = check_redis()
    ready = db_ok and redis_ok
    return {
        "status": "ready" if ready else "degraded",
        "timestamp": datetime.now(UTC).isoformat(),
        "checks": {
            "database": {"ok": db_ok, "detail": db_msg},
            "redis": {"ok": redis_ok, "detail": redis_msg},
        },
    }
