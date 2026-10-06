from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base

class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    __table_args__ = {"schema": "public"}

    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("public.users.id"))
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    expired_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
