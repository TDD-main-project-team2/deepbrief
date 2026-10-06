from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Identity, String, text
from sqlalchemy.orm import Mapped, mapped_column

class UrlArticle():
    __tablename__ = "url_articles"
    __table_args__ = {"schema": "public"}

    input_id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("public.users.user_id"), nullable=False)
    article_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("public.articles.article_id"), nullable=True)
    submitted_url: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
