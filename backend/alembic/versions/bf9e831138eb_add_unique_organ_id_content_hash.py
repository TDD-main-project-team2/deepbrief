"""add unique organ id content hash

Revision ID: bf9e831138eb
Revises: 0ff8c065858e
Create Date: 2026-10-23 11:57:30.988118

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bf9e831138eb'
down_revision: Union[str, Sequence[str], None] = '0ff8c065858e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('articles', sa.Column('organization_id', sa.BigInteger(), nullable=False))
    op.drop_constraint(op.f('uq_articles_content_hash'), 'articles', type_='unique')
    op.create_unique_constraint('uq_articles_organization_content_hash', 'articles', ['organization_id', 'content_hash'])
    op.create_foreign_key("fk_articles_organization_id", 'articles', 'organizations', ['organization_id'], ['id'])
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("fk_articles_organization_id", 'articles', type_='foreignkey')
    op.drop_constraint('uq_articles_organization_content_hash', 'articles', type_='unique')
    op.create_unique_constraint(op.f('uq_articles_content_hash'), 'articles', ['content_hash'], postgresql_nulls_not_distinct=False)
    op.drop_column('articles', 'organization_id')
    # ### end Alembic commands ###
