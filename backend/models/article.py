from backend.models.base import Base
from sqlalchemy import CheckConstraint, String, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime


class Article(Base):
    __tablename__ = "articles"
    __table_args__ = (
        CheckConstraint("content_hash = btrim(content_hash) AND content_hash <> ''", name="check_content_hash_not_empty"),
        CheckConstraint("visibility IN ('private', 'public')", name="check_visibility"),
        CheckConstraint("title = btrim(title) AND title <> ''", name="check_title_not_empty"),
        CheckConstraint("body = btrim(body) AND body <> ''", name="check_body_not_empty"),
        CheckConstraint("media = btrim(media) AND media <> ''", name="check_media_not_empty"),
        CheckConstraint("author = btrim(author) AND author <> ''", name="check_author_not_empty"),
        CheckConstraint("category = btrim(category) AND category <> ''", name="check_category_not_empty"),
    )

    content_hash: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    visibility: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="private"
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    media: Mapped[str | None] = mapped_column(String(255), nullable=True)
    author: Mapped[str | None] = mapped_column(String(255), nullable=True)
    category: Mapped[str | None] = mapped_column(String(255), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
