from sqlalchemy import CheckConstraint, BigInteger, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base

class UrlArticle(Base):
    __tablename__ = "url_articles"
    __table_args__ = (
        CheckConstraint(
            "submitted_url = btrim(submitted_url) AND submitted_url <> ''",
            name="check_url_article_submitted_url_not_empty",
        ),
        {"schema": "public"},
    )

    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("public.users.id"), nullable=False)
    article_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("public.articles.id"), nullable=True)
    submitted_url: Mapped[str] = mapped_column(String(255), nullable=False)
