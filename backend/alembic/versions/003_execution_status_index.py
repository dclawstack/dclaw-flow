"""Execution status/date index for history queries

Revision ID: 003
Revises: 002
Create Date: 2026-06-22 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Supports status + date-range filtering and the retention cleanup scan.
    op.create_index(
        "idx_executions_status_started",
        "executions",
        ["status", "started_at"],
    )


def downgrade() -> None:
    op.drop_index("idx_executions_status_started", table_name="executions")
