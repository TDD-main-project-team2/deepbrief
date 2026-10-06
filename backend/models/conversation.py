from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, text
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base

class Conversation(Base):
    __tablename__ = "conversations"
    __table_args__ = {"schema": "public"}

    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("public.users.id"))
    title: Mapped[str] = mapped_column(String(255), nullable=False)
