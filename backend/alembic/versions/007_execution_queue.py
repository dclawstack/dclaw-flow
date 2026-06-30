"""Durable execution queue: lease + attempts on executions

Revision ID: 007
Revises: 006
Create Date: 2026-06-30 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "executions",
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "executions",
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
    )
    # Worker poll predicate: pending jobs whose lease is free.
    op.create_index(
        "ix_executions_queue",
        "executions",
        ["status", "locked_until"],
    )


def downgrade() -> None:
    op.drop_index("ix_executions_queue", table_name="executions")
    op.drop_column("executions", "attempts")
    op.drop_column("executions", "locked_until")
