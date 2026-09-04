import logging
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from jose import JWTError, jwt
import bcrypt

from app.core.config import settings

logger = logging.getLogger(__name__)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def create_access_token(subject: str, org_id: UUID, role: str, **extra: Any) -> str:
    expire = datetime.now(UTC) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {"sub": subject, "org_id": str(org_id), "role": role, "exp": expire, **extra}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise ValueError("Invalid token") from exc


def verify_whatsapp_signature(payload: bytes, signature_header: str | None) -> bool:
    """Verify Meta X-Hub-Signature-256 when app secret is configured."""
    if not settings.whatsapp_app_secret:
        logger.warning("WhatsApp app secret not configured; skipping signature verification")
        return True
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    import hashlib
    import hmac

    expected = hmac.new(
        settings.whatsapp_app_secret.encode(),
        payload,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(signature_header[7:], expected)
