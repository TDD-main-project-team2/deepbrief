from backend.models.base import Base
from sqlalchemy import BigInteger, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column


class UserArticle(Base):
    __tablename__ = "user_articles"

    id = None
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False, primary_key=True)
    article_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("articles.id"), nullable=False, primary_key=True)
