from backend.models.base import Base
from sqlalchemy import BigInteger, String, ForeignKey, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column


class File(Base):
    __tablename__ = "files"
    __table_args__ = (
        CheckConstraint("size_bytes >= 0", name="check_size_bytes_nonnegative"),
        CheckConstraint("title = btrim(title) AND title <> ''", name="check_title_not_empty"),
        CheckConstraint("mime_type = btrim(mime_type) AND mime_type <> ''", name="check_mime_type_not_empty")
    )

    article_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("articles.id"), nullable=False, unique=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(255), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
