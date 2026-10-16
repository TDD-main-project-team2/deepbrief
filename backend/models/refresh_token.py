from backend.models.base import Base
from sqlalchemy import CheckConstraint, BigInteger, String, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    __table_args__ = (
        CheckConstraint("token_hash = btrim(token_hash) AND token_hash <> ''", name="check_token_hash_not_empty"),
    )

    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    expired_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
