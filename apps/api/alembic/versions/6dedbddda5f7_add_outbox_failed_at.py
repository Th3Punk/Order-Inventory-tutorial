"""add outbox failed_at

Revision ID: 6dedbddda5f7
Revises: 69170cf52910
Create Date: 2026-02-08 14:30:10.613074

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "6dedbddda5f7"
down_revision: Union[str, Sequence[str], None] = "69170cf52910"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "outbox_events",
        sa.Column("failed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_outbox_events_failed_at", "outbox_events", ["failed_at"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_outbox_events_failed_at", table_name="outbox_events")
    op.drop_column("outbox_events", "failed_at")
