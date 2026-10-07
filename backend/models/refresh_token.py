from datetime import datetime

from sqlalchemy import CheckConstraint, BigInteger, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base

class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    __table_args__ = (
        CheckConstraint(
            "token_hash = btrim(token_hash) AND token_hash <> ''",
            name="check_refresh_token_token_hash_not_empty",
        ),
        {"schema": "public"},
    )

    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("public.users.id"))
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    expired_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
