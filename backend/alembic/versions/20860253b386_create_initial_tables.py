"""create initial tables

Revision ID: 20860253b386
Revises: 
Create Date: 2026-10-07 08:52:12.504331

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '20860253b386'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

UPDATED_AT_TABLES = (
    "users",
    "articles",
    "conversations",
    "messages",
    "url_articles",
    "file_articles",
    "user_articles",
    "refresh_tokens",
)

def upgrade() -> None:
    """Upgrade schema."""

    # 테이블 생성
    op.create_table('articles',
    sa.Column('title', sa.String(length=255), nullable=False),
    sa.Column('body', sa.Text(), nullable=False),
    sa.Column('content_hash', sa.String(length=255), nullable=False),
    sa.Column('publisher', sa.String(length=255), nullable=True),
    sa.Column('author', sa.String(length=255), nullable=True),
    sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('source_url', sa.String(length=255), nullable=True),
    sa.Column('category', sa.String(length=255), nullable=True),
    sa.Column('language', sa.String(length=255), nullable=True),
    sa.Column('id', sa.BigInteger(), sa.Identity(always=True), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    schema='public'
    )
    op.create_table('users',
    sa.Column('email', sa.String(length=255), nullable=False),
    sa.Column('password_hash', sa.String(length=255), nullable=False),
    sa.Column('nickname', sa.String(length=255), nullable=False),
    sa.Column('id', sa.BigInteger(), sa.Identity(always=True), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    schema='public'
    )
    op.create_table('conversations',
    sa.Column('user_id', sa.BigInteger(), nullable=False),
    sa.Column('title', sa.String(length=255), nullable=False),
    sa.Column('id', sa.BigInteger(), sa.Identity(always=True), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['public.users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    schema='public'
    )
    op.create_table('file_articles',
    sa.Column('user_id', sa.BigInteger(), nullable=False),
    sa.Column('article_id', sa.BigInteger(), nullable=True),
    sa.Column('original_filename', sa.String(length=255), nullable=False),
    sa.Column('mime_type', sa.String(length=255), nullable=False),
    sa.Column('file_size_bytes', sa.BigInteger(), nullable=False),
    sa.Column('id', sa.BigInteger(), sa.Identity(always=True), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    sa.ForeignKeyConstraint(['article_id'], ['public.articles.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['public.users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    schema='public'
    )
    op.create_table('refresh_tokens',
    sa.Column('user_id', sa.BigInteger(), nullable=False),
    sa.Column('token_hash', sa.String(length=255), nullable=False),
    sa.Column('expired_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('id', sa.BigInteger(), sa.Identity(always=True), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['public.users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    schema='public'
    )
    op.create_table('url_articles',
    sa.Column('user_id', sa.BigInteger(), nullable=False),
    sa.Column('article_id', sa.BigInteger(), nullable=True),
    sa.Column('submitted_url', sa.String(length=255), nullable=False),
    sa.Column('id', sa.BigInteger(), sa.Identity(always=True), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    sa.ForeignKeyConstraint(['article_id'], ['public.articles.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['public.users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    schema='public'
    )
    op.create_table('user_articles',
    sa.Column('user_id', sa.BigInteger(), nullable=False),
    sa.Column('article_id', sa.BigInteger(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    sa.ForeignKeyConstraint(['article_id'], ['public.articles.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['public.users.id'], ),
    sa.PrimaryKeyConstraint('user_id', 'article_id'),
    schema='public'
    )
    op.create_table('messages',
    sa.Column('conversation_id', sa.BigInteger(), nullable=False),
    sa.Column('role', sa.String(length=255), nullable=False),
    sa.Column('content', sa.Text(), nullable=False),
    sa.Column('id', sa.BigInteger(), sa.Identity(always=True), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    sa.ForeignKeyConstraint(['conversation_id'], ['public.conversations.id'], ),
    sa.PrimaryKeyConstraint('id'),
    schema='public'
    )

    # updated_at 컬럼을 자동으로 갱신하는 함수 생성
    op.execute(
        """
        CREATE FUNCTION public.set_updated_at()
        RETURNS TRIGGER 
        LANGUAGE plpgsql
        AS $$
        BEGIN
            NEW.updated_at = clock_timestamp();
            RETURN NEW;
        END;
        $$;
        """
    )

    # 트리거 생성
    for table in UPDATED_AT_TABLES:
        op.execute(
            f"""
            CREATE TRIGGER {table}_set_updated_at
            BEFORE UPDATE ON public.{table}
            FOR EACH ROW
            EXECUTE FUNCTION public.set_updated_at();
            """
        )


def downgrade() -> None:
    """Downgrade schema."""
    
    for table in reversed(UPDATED_AT_TABLES):
        op.execute(
            f"""
            DROP TRIGGER IF EXISTS {table}_set_updated_at 
            ON public.{table};
            """
        )
    op.execute("DROP FUNCTION public.set_updated_at();")

    op.drop_table('messages', schema='public')
    op.drop_table('user_articles', schema='public')
    op.drop_table('url_articles', schema='public')
    op.drop_table('refresh_tokens', schema='public')
    op.drop_table('file_articles', schema='public')
    op.drop_table('conversations', schema='public')
    op.drop_table('users', schema='public')
    op.drop_table('articles', schema='public')
