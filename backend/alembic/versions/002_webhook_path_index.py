"""Webhook path lookup index

Revision ID: 002
Revises: 001
Create Date: 2026-06-22 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Partial expression index so webhook ingestion is an O(log n) lookup by path
    # instead of a scan over active workflows.
    op.execute(
        "CREATE INDEX idx_workflows_webhook_path "
        "ON workflows ((trigger -> 'config' ->> 'path')) "
        "WHERE status = 'active'"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_workflows_webhook_path")
