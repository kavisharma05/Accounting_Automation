"""Production hardening tests."""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

import app.models.entities  # noqa: F401
from app.core.rate_limit import RateLimiter
from app.core.startup import validate_production_settings
from app.main import app as fastapi_app


def test_rate_limiter_blocks_excess():
    limiter = RateLimiter(max_requests=3, window_seconds=60)
    assert limiter.allow("1.2.3.4") is True
    assert limiter.allow("1.2.3.4") is True
    assert limiter.allow("1.2.3.4") is True
    assert limiter.allow("1.2.3.4") is False


def test_production_config_rejects_weak_secret():
    with patch("app.core.startup.settings") as mock_settings:
        mock_settings.is_production = True
        mock_settings.secret_key = "change-me"
        mock_settings.debug = False
        mock_settings.messaging_provider = "mock"
        mock_settings.document_provider = "mock"
        with pytest.raises(RuntimeError, match="SECRET_KEY"):
            validate_production_settings()


def test_health_live_endpoint():
    with TestClient(fastapi_app) as client:
        resp = client.get("/api/v1/health/live")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


def test_health_ready_endpoint_sqlite():
    """Readiness may degrade without Redis in unit test — live endpoint always ok."""
    with TestClient(fastapi_app) as client:
        resp = client.get("/api/v1/health/ready")
        assert resp.status_code in (200, 503)
        body = resp.json()
        assert "checks" in body or "detail" in body
