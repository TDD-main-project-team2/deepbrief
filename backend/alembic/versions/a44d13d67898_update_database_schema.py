"""Update the relational schema (existing application tables must be empty).

Revision ID: a44d13d67898
Revises: d8548f0a43da

No data migration is performed. Downgrade restores structure, not deleted data.
"""
from alembic import op
import sqlalchemy as sa

revision = "a44d13d67898"
down_revision = "d8548f0a43da"
branch_labels = None
depends_on = None

NEW_TABLES = ("organizations", "files", "guidelines", "templates")

# Existing CHECK expressions stay unchanged; only their names change.
RENAMED_CHECKS = (
    ("articles", "check_article_title_not_empty", "check_title_not_empty"),
    ("articles", "check_article_body_not_empty", "check_body_not_empty"),
    ("articles", "check_article_content_hash_not_empty", "check_content_hash_not_empty"),
    ("articles", "check_article_author_not_empty", "check_author_not_empty"),
    ("articles", "check_article_category_not_empty", "check_category_not_empty"),
    ("conversations", "check_conversation_title_not_empty", "check_title_not_empty"),
    ("messages", "check_message_role", "check_role"),
    ("messages", "check_message_content_not_empty", "check_content_not_empty"),
    ("refresh_tokens", "check_refresh_token_token_hash_not_empty", "check_token_hash_not_empty"),
)
ADDED_CHECKS = (
    ("articles", "check_media_not_empty", "media = btrim(media) AND media <> ''"),
    ("article_chunks", "check_content_not_empty", "content = btrim(content) AND content <> ''"),
    ("article_chunks", "check_chunk_index_nonnegative", "chunk_index >= 0"),
)


def _create_updated_at_trigger(table: str) -> None:
    # Table names are fixed migration constants, never user input.
    op.execute(f"""
        CREATE TRIGGER {table}_set_updated_at
        BEFORE UPDATE ON public.{table}
        FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
    """)


def upgrade() -> None:
    # 테이블 생성
    op.create_table('organizations',
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('id', sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.CheckConstraint("code = btrim(code) AND code <> ''", name='check_code_not_empty'),
        sa.CheckConstraint("name = btrim(name) AND name <> ''", name='check_name_not_empty'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code', name='uq_organizations_code'),
        schema='public',
    )
    op.create_table('files',
        sa.Column('article_id', sa.BigInteger(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('mime_type', sa.String(length=255), nullable=False),
        sa.Column('size_bytes', sa.BigInteger(), nullable=False),
        sa.Column('id', sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.CheckConstraint("mime_type = btrim(mime_type) AND mime_type <> ''", name='check_mime_type_not_empty'),
        sa.CheckConstraint("title = btrim(title) AND title <> ''", name='check_title_not_empty'),
        sa.CheckConstraint('size_bytes >= 0', name='check_size_bytes_nonnegative'),
        sa.ForeignKeyConstraint(['article_id'], ['public.articles.id'], name='files_article_id_fkey'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('article_id', name='uq_files_article_id'),
        schema='public',
    )
    op.create_table('guidelines',
        sa.Column('organization_id', sa.BigInteger(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('id', sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.CheckConstraint("content = btrim(content) AND content <> ''", name='check_content_not_empty'),
        sa.CheckConstraint("title = btrim(title) AND title <> ''", name='check_title_not_empty'),
        sa.ForeignKeyConstraint(['organization_id'], ['public.organizations.id'], name='guidelines_organization_id_fkey'),
        sa.PrimaryKeyConstraint('id'),
        schema='public',
    )
    op.create_table('templates',
        sa.Column('organization_id', sa.BigInteger(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('id', sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.CheckConstraint("content = btrim(content) AND content <> ''", name='check_content_not_empty'),
        sa.CheckConstraint("title = btrim(title) AND title <> ''", name='check_title_not_empty'),
        sa.ForeignKeyConstraint(['organization_id'], ['public.organizations.id'], name='templates_organization_id_fkey'),
        sa.PrimaryKeyConstraint('id'),
        schema='public',
    )

    # 테이블 삭제 (기존 업로드 데이터는 복사하지 않음)
    op.drop_table("file_articles", schema="public")
    op.drop_table("url_articles", schema="public")

    # 컬럼 추가
    op.add_column("articles", sa.Column("media", sa.String(255), nullable=True), schema="public")
    op.add_column("conversations", sa.Column("article_id", sa.BigInteger(), nullable=False), schema="public")
    op.add_column("users", sa.Column("organization_id", sa.BigInteger(), nullable=False), schema="public")

    # 컬럼 삭제
    for column in ("language", "source_url", "publisher"):
        # PostgreSQL removes the single-column CHECK with the dropped column.
        op.drop_column("articles", column, schema="public")

    # UNIQUE 제약조건 생성
    op.create_unique_constraint("uq_articles_content_hash", "articles", ["content_hash"], schema="public")
    op.create_unique_constraint("uq_conversations_user_article", "conversations", ["user_id", "article_id"], schema="public")
    op.create_unique_constraint("uq_refresh_tokens_token_hash", "refresh_tokens", ["token_hash"], schema="public")

    # 외래키 생성
    op.create_foreign_key("conversations_article_id_fkey", "conversations", "articles", ["article_id"], ["id"], source_schema="public", referent_schema="public")
    op.create_foreign_key("users_organization_id_fkey", "users", "organizations", ["organization_id"], ["id"], source_schema="public", referent_schema="public")

    # CHECK 제약조건 이름 변경
    for table, old_name, new_name in RENAMED_CHECKS:
        op.execute(f"ALTER TABLE public.{table} RENAME CONSTRAINT {old_name} TO {new_name}")

    # CHECK 제약조건 생성
    for table, name, condition in ADDED_CHECKS:
        op.create_check_constraint(name, table, condition, schema="public")

    # 트리거 생성
    for table in NEW_TABLES:
        _create_updated_at_trigger(table)


def downgrade() -> None:
    # 제약조건 삭제 (참조하는 컬럼보다 먼저 삭제)
    for table, name, _ in reversed(ADDED_CHECKS):
        op.drop_constraint(name, table, type_="check", schema="public")
    op.drop_constraint("users_organization_id_fkey", "users", type_="foreignkey", schema="public")
    op.drop_constraint("uq_refresh_tokens_token_hash", "refresh_tokens", type_="unique", schema="public")
    op.drop_constraint("conversations_article_id_fkey", "conversations", type_="foreignkey", schema="public")
    op.drop_constraint("uq_conversations_user_article", "conversations", type_="unique", schema="public")
    op.drop_constraint("uq_articles_content_hash", "articles", type_="unique", schema="public")

    # 컬럼 삭제
    op.drop_column("users", "organization_id", schema="public")
    op.drop_column("conversations", "article_id", schema="public")
    op.drop_column("articles", "media", schema="public")

    # 테이블 삭제 (자식 테이블부터 삭제)
    for table in reversed(NEW_TABLES):
        # Table deletion also removes that table's triggers and constraints.
        op.drop_table(table, schema="public")

    # 테이블 복원
    op.create_table('url_articles',
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('article_id', sa.BigInteger(), nullable=True),
        sa.Column('submitted_url', sa.String(255), nullable=False),
        sa.Column('id', sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.CheckConstraint("submitted_url = btrim(submitted_url) AND submitted_url <> ''", name=op.f('check_url_article_submitted_url_not_empty')),
        sa.ForeignKeyConstraint(['article_id'], ['public.articles.id'], name=op.f('url_articles_article_id_fkey')),
        sa.ForeignKeyConstraint(['user_id'], ['public.users.id'], name=op.f('url_articles_user_id_fkey')),
        sa.PrimaryKeyConstraint('id', name=op.f('url_articles_pkey')),
        schema='public',
    )
    op.create_table('file_articles',
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('article_id', sa.BigInteger(), nullable=True),
        sa.Column('original_filename', sa.String(255), nullable=False),
        sa.Column('mime_type', sa.String(255), nullable=False),
        sa.Column('file_size_bytes', sa.BigInteger(), nullable=False),
        sa.Column('id', sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.CheckConstraint("mime_type = btrim(mime_type) AND mime_type <> ''", name=op.f('check_file_article_mime_type_not_empty')),
        sa.CheckConstraint("original_filename = btrim(original_filename) AND original_filename <> ''", name=op.f('check_file_article_original_filename_not_empty')),
        sa.CheckConstraint('file_size_bytes >= 0', name=op.f('check_file_article_size_nonnegative')),
        sa.ForeignKeyConstraint(['article_id'], ['public.articles.id'], name=op.f('file_articles_article_id_fkey')),
        sa.ForeignKeyConstraint(['user_id'], ['public.users.id'], name=op.f('file_articles_user_id_fkey')),
        sa.PrimaryKeyConstraint('id', name=op.f('file_articles_pkey')),
        schema='public',
    )

    # 컬럼 복원
    for column in ("publisher", "source_url", "language"):
        op.add_column("articles", sa.Column(column, sa.String(255), nullable=True), schema="public")

    # CHECK 제약조건 복원
    for table, old_name, new_name in reversed(RENAMED_CHECKS):
        op.execute(f"ALTER TABLE public.{table} RENAME CONSTRAINT {new_name} TO {old_name}")
    for column in ("publisher", "source_url", "language"):
        op.create_check_constraint(
            f"check_article_{column}_not_empty", "articles",
            f"{column} = btrim({column}) AND {column} <> ''", schema="public",
        )

    # 트리거 복원
    for table in ("url_articles", "file_articles"):
        _create_updated_at_trigger(table)
    # public.set_updated_at() is shared with the remaining tables; keep it.
