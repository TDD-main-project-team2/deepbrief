from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Identity, String, text
from sqlalchemy.orm import Mapped, mapped_column

class Article():
    __tablename__ = "articles"
    __table_args__ = {"schema": "public"}

    article_id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(String(255), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    publisher: Mapped[str] = mapped_column(String(255))
    author: Mapped[str] = mapped_column(String(255))
    published_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP")
    )
    source_url: Mapped[str] = mapped_column(String(255))
    category: Mapped[str] = mapped_column(String(255))
    language: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
