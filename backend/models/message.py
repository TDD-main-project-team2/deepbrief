from sqlalchemy import BigInteger, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base

class Message(Base):
    __tablename__ = "messages"
    __table_args__ = {"schema": "public"}

    conversation_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("public.conversations.id"))
    role: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
