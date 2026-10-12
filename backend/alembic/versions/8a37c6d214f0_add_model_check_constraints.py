"""Add CHECK constraints declared by the relational models.

Revision ID: 8a37c6d214f0
Revises: 20860253b386
"""
from alembic import op

revision = "8a37c6d214f0"
down_revision = "20860253b386"
branch_labels = None
depends_on = None

CHECK_CONSTRAINTS = (
    ('articles', 'check_article_title_not_empty', "title = btrim(title) AND title <> ''"),
    ('articles', 'check_article_body_not_empty', "body = btrim(body) AND body <> ''"),
    ('articles', 'check_article_content_hash_not_empty', "content_hash = btrim(content_hash) AND content_hash <> ''"),
    ('articles', 'check_article_publisher_not_empty', "publisher = btrim(publisher) AND publisher <> ''"),
    ('articles', 'check_article_author_not_empty', "author = btrim(author) AND author <> ''"),
    ('articles', 'check_article_source_url_not_empty', "source_url = btrim(source_url) AND source_url <> ''"),
    ('articles', 'check_article_category_not_empty', "category = btrim(category) AND category <> ''"),
    ('articles', 'check_article_language_not_empty', "language = btrim(language) AND language <> ''"),
    ('conversations', 'check_conversation_title_not_empty', "title = btrim(title) AND title <> ''"),
    ('file_articles', 'check_file_article_original_filename_not_empty', "original_filename = btrim(original_filename) AND original_filename <> ''"),
    ('file_articles', 'check_file_article_mime_type_not_empty', "mime_type = btrim(mime_type) AND mime_type <> ''"),
    ('file_articles', 'check_file_article_size_nonnegative', 'file_size_bytes >= 0'),
    ('messages', 'check_message_role', "role IN ('user', 'assistant')"),
    ('messages', 'check_message_content_not_empty', "content = btrim(content) AND content <> ''"),
    ('refresh_tokens', 'check_refresh_token_token_hash_not_empty', "token_hash = btrim(token_hash) AND token_hash <> ''"),
    ('url_articles', 'check_url_article_submitted_url_not_empty', "submitted_url = btrim(submitted_url) AND submitted_url <> ''"),
    ('users', 'check_email_not_empty', "email = btrim(email) AND email <> ''"),
    ('users', 'check_password_hash_not_empty', "password_hash = btrim(password_hash) AND password_hash <> ''"),
    ('users', 'check_nickname_not_empty', "nickname = btrim(nickname) AND nickname <> ''"),
)


def upgrade() -> None:
    for table, name, condition in CHECK_CONSTRAINTS:
        op.create_check_constraint(name, table, condition, schema="public")


def downgrade() -> None:
    for table, name, _ in reversed(CHECK_CONSTRAINTS):
        op.drop_constraint(name, table, type_="check", schema="public")
