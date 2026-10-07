from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base

class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (
        CheckConstraint(
            "role IN ('user', 'assistant')",
            name="check_message_role",
        ),
        CheckConstraint(
            "content = btrim(content) AND content <> ''",
            name="check_message_content_not_empty",
        ),
        {"schema": "public"},
    )

    conversation_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("public.conversations.id"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
