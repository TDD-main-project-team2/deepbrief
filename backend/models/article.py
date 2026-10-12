from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base

class Article(Base):
    __tablename__ = "articles"
    __table_args__ = (
        CheckConstraint(
            "title = btrim(title) AND title <> ''",
            name="check_article_title_not_empty",
        ),
        CheckConstraint(
            "body = btrim(body) AND body <> ''",
            name="check_article_body_not_empty",
        ),
        CheckConstraint(
            "content_hash = btrim(content_hash) AND content_hash <> ''",
            name="check_article_content_hash_not_empty",
        ),
        CheckConstraint(
            "publisher = btrim(publisher) AND publisher <> ''",
            name="check_article_publisher_not_empty",
        ),
        CheckConstraint(
            "author = btrim(author) AND author <> ''",
            name="check_article_author_not_empty",
        ),
        CheckConstraint(
            "source_url = btrim(source_url) AND source_url <> ''",
            name="check_article_source_url_not_empty",
        ),
        CheckConstraint(
            "category = btrim(category) AND category <> ''",
            name="check_article_category_not_empty",
        ),
        CheckConstraint(
            "language = btrim(language) AND language <> ''",
            name="check_article_language_not_empty",
        ),
        {"schema": "public"},
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    publisher: Mapped[str | None] = mapped_column(String(255))
    author: Mapped[str | None] = mapped_column(String(255))
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    source_url: Mapped[str | None] = mapped_column(String(255))
    category: Mapped[str | None] = mapped_column(String(255))
    language: Mapped[str | None] = mapped_column(String(255))
