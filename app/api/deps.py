from uuid import UUID

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.logging import OrganizationContext
from app.core.security import decode_access_token


def get_current_ctx(
    db: Session = Depends(get_db),
    authorization: str | None = Header(default=None),
    x_organization_id: str | None = Header(default=None),
) -> OrganizationContext:
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]
        try:
            payload = decode_access_token(token)
            return OrganizationContext(
                organization_id=UUID(payload["org_id"]),
                user_id=UUID(payload["sub"]),
                role=payload.get("role"),
            )
        except ValueError as exc:
            raise HTTPException(401, "Invalid token") from exc

    if x_organization_id:
        return OrganizationContext(
            organization_id=UUID(x_organization_id),
            role="owner",  # dev/pilot header; use JWT in production
        )

    raise HTTPException(401, "Authentication required")
