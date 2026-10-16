from backend.models.base import Base
from sqlalchemy import CheckConstraint, BigInteger, String, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column


class Conversation(Base):
    __tablename__ = "conversations"
    __table_args__ = (
        UniqueConstraint("user_id", "article_id", name="uq_conversations_user_article"),
        CheckConstraint("title = btrim(title) AND title <> ''", name="check_title_not_empty"),
    )

    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)
    article_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("articles.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
