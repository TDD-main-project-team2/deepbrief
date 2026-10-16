"""add article visibility

Revision ID: bb86aa359141
Revises: a44d13d67898
Create Date: 2026-10-16 09:20:25.333630

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bb86aa359141'
down_revision: Union[str, Sequence[str], None] = 'a44d13d67898'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('articles', sa.Column('visibility', sa.String(length=20), server_default='private', nullable=False))
    op.create_check_constraint(
        "check_visibility",
        "articles",
        "visibility IN ('private', 'public')",
    )


def downgrade() -> None:
    op.drop_constraint(
        "check_visibility",
        "articles",
        type_="check",
    )
    op.drop_column('articles', 'visibility')
