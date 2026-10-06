from datetime import datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base

class Article(Base):
    __tablename__ = "articles"
    __table_args__ = {"schema": "public"}

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
