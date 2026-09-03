from uuid import UUID

from fastapi import Depends, HTTPException

from app.api.deps import get_current_ctx
from app.core.logging import OrganizationContext

WRITE_ROLES = {"owner", "accountant", "admin"}
READ_ROLES = {"owner", "accountant", "viewer", "admin"}


def require_role(*allowed: str):
    def _dep(ctx: OrganizationContext = Depends(get_current_ctx)) -> OrganizationContext:
        if ctx.role and ctx.role not in allowed:
            raise HTTPException(403, f"Role '{ctx.role}' not permitted")
        return ctx

    return _dep


require_write = require_role(*WRITE_ROLES)
require_read = require_role(*READ_ROLES)


def ensure_org_access(ctx: OrganizationContext, org_id: UUID) -> None:
    if ctx.organization_id != org_id:
        raise HTTPException(403, "Organization mismatch")
