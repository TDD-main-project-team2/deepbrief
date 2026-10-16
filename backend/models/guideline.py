from backend.models.base import Base
from sqlalchemy import CheckConstraint, BigInteger, String, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column


class Guideline(Base):
    __tablename__ = "guidelines"
    __table_args__ = (
        CheckConstraint("title = btrim(title) AND title <> ''", name="check_title_not_empty"),
        CheckConstraint("content = btrim(content) AND content <> ''", name="check_content_not_empty")
    )

    organization_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("organizations.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
