import logging
from dataclasses import dataclass
from uuid import UUID

logger = logging.getLogger(__name__)


def configure_logging(debug: bool = False) -> None:
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )


@dataclass(frozen=True)
class OrganizationContext:
    organization_id: UUID
    user_id: UUID | None = None
    role: str | None = None
    phone: str | None = None

    def ensure_org(self, resource_org_id: UUID) -> None:
        from app.core.exceptions import TenantIsolationError

        if resource_org_id != self.organization_id:
            raise TenantIsolationError("Cross-tenant access denied")
