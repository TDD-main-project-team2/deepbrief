from sqlalchemy import CheckConstraint, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base

class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "email = btrim(email) AND email <> ''",
            name="check_email_not_empty",
        ),
        CheckConstraint(
            "password_hash = btrim(password_hash) AND password_hash <> ''",
            name="check_password_hash_not_empty",
        ),
        CheckConstraint(
            "nickname = btrim(nickname) AND nickname <> ''",
            name="check_nickname_not_empty",
        ),
        {"schema": "public"},
    )

    email: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    nickname: Mapped[str] = mapped_column(String(255), nullable=False)
