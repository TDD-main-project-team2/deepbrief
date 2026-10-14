"""add_article_chunk_table

Revision ID: d8548f0a43da
Revises: 86eaa7359caa
Create Date: 2026-10-13 09:57:32.623025

"""
from typing import Sequence, Union

from alembic import op
from pgvector.sqlalchemy import Vector
import sqlalchemy as sa


revision: str = 'd8548f0a43da'
down_revision: Union[str, Sequence[str], None] = '86eaa7359caa'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """청크 테이블과 수정 시각 갱신 트리거를 생성한다."""
    
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    op.create_table('article_chunks',
    sa.Column('article_id', sa.BigInteger(), nullable=False),
    sa.Column('chunk_index', sa.Integer(), nullable=False),
    sa.Column('content', sa.Text(), nullable=False),
    sa.Column('embedding', Vector(1024), nullable=False),
    sa.Column('id', sa.BigInteger(), sa.Identity(always=True), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    sa.ForeignKeyConstraint(['article_id'], ['public.articles.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('article_id', 'chunk_index', name='uq_article_chunks_article_id_chunk_index'),
    schema='public'
    )

    op.execute("""
        CREATE TRIGGER article_chunks_set_updated_at
        BEFORE UPDATE ON public.article_chunks
        FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
    """)


def downgrade() -> None:
    """청크 테이블과 수정 시각 갱신 트리거를 삭제한다."""

    op.execute("""
        DROP TRIGGER article_chunks_set_updated_at
        ON public.article_chunks;
    """)
    op.drop_table('article_chunks', schema='public')
