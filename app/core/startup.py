"""Production startup validation."""

import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

_INSECURE_SECRETS = {
    "change-me",
    "dev-secret-change-in-production",
    "change-me-to-random-64-char-string",
}


def validate_production_settings() -> None:
    if not settings.is_production:
        return

    errors: list[str] = []
    if settings.secret_key in _INSECURE_SECRETS or len(settings.secret_key) < 32:
        errors.append("SECRET_KEY must be a strong random string (32+ chars) in production")
    if settings.debug:
        errors.append("DEBUG must be false in production")
    if settings.messaging_provider == "whatsapp" and not settings.whatsapp_app_secret:
        errors.append("WHATSAPP_APP_SECRET required when MESSAGING_PROVIDER=whatsapp")
    if settings.document_provider == "claude" and not settings.anthropic_api_key:
        errors.append("ANTHROPIC_API_KEY required when DOCUMENT_PROVIDER=claude")

    if errors:
        for msg in errors:
            logger.error("Production config error: %s", msg)
        raise RuntimeError(f"Invalid production configuration: {'; '.join(errors)}")

    logger.info("Production settings validated")
