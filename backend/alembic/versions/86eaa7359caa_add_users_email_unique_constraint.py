"""add users email unique constraint

Revision ID: 86eaa7359caa
Revises: 8a37c6d214f0
Create Date: 2026-10-08 21:59:23.047588

"""
from typing import Sequence, Union

from alembic import op


revision: str = '86eaa7359caa'
down_revision: Union[str, Sequence[str], None] = '8a37c6d214f0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_unique_constraint(
        "unique_users_email",
        "users",
        ["email"],
        schema="public",
    )


def downgrade() -> None:
    op.drop_constraint(
        "unique_users_email",
        "users",
        schema="public",
        type_="unique",
    )
