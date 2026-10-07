from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base

class Conversation(Base):
    __tablename__ = "conversations"
    __table_args__ = (
        CheckConstraint(
            "title = btrim(title) AND title <> ''",
            name="check_conversation_title_not_empty",
        ),
        {"schema": "public"},
    )

    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("public.users.id"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
