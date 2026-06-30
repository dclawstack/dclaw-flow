"""Workflow owner FK + system-user backfill (auth enforcement)

Revision ID: 006
Revises: 005
Create Date: 2026-06-30 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SYSTEM_USER = "00000000-0000-0000-0000-000000000000"


def upgrade() -> None:
    # A non-loginable system user owns all pre-auth (orphan) workflows. The '!'
    # password is not a valid bcrypt hash, so the account can never authenticate.
    op.execute(
        "INSERT INTO users (id, email, hashed_password, created_at) "
        f"VALUES ('{SYSTEM_USER}', 'system@dclaw.local', '!', now()) "
        "ON CONFLICT (id) DO NOTHING"
    )
    op.execute(
        "UPDATE workflows SET owner_id = '" + SYSTEM_USER + "' "
        "WHERE owner_id NOT IN (SELECT id FROM users)"
    )
    op.create_foreign_key(
        "fk_workflows_owner_id_users", "workflows", "users", ["owner_id"], ["id"]
    )


def downgrade() -> None:
    op.drop_constraint("fk_workflows_owner_id_users", "workflows", type_="foreignkey")
