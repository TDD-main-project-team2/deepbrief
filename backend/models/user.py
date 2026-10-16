from backend.models.base import Base
from sqlalchemy import CheckConstraint, BigInteger, String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("nickname = btrim(nickname) AND nickname <> ''", name="check_nickname_not_empty"),
        CheckConstraint("email = btrim(email) AND email <> ''", name="check_email_not_empty"),
        CheckConstraint("password_hash = btrim(password_hash) AND password_hash <> ''", name="check_password_hash_not_empty")
    )

    organization_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("organizations.id"), nullable=False)
    nickname: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
