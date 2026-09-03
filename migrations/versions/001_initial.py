"""Initial schema — creates all tables from SQLAlchemy metadata.

Revision ID: 001
"""

from alembic import op

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    import app.models.entities  # noqa: F401
    from app.core.database import Base

    bind = op.get_bind()
    Base.metadata.create_all(bind)


def downgrade() -> None:
    import app.models.entities  # noqa: F401
    from app.core.database import Base

    bind = op.get_bind()
    Base.metadata.drop_all(bind)
