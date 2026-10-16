from backend.models.base import Base
from sqlalchemy import CheckConstraint, String
from sqlalchemy.orm import Mapped, mapped_column


class Organization(Base):
    __tablename__ = "organizations"
    __table_args__ = (
        CheckConstraint("name = btrim(name) AND name <> ''", name="check_name_not_empty"),
        CheckConstraint("code = btrim(code) AND code <> ''", name="check_code_not_empty")
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
