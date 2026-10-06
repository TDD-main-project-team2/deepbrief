from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base

class User(Base):
    __tablename__ = "users"
    __table_args__ = {"schema": "public"}

    email: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    nickname: Mapped[str] = mapped_column(String(255), nullable=False)
