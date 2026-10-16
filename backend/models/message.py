from backend.models.base import Base
from sqlalchemy import BigInteger, String, Text, ForeignKey, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (
        CheckConstraint("role IN ('user', 'assistant')", name="check_role"),
        CheckConstraint("content = btrim(content) AND content <> ''", name="check_content_not_empty")
    )

    conversation_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("conversations.id"), nullable=False)
    role: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
