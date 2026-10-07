from sqlalchemy import CheckConstraint, BigInteger, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base

class FileArticle(Base):
    __tablename__ = "file_articles"
    __table_args__ = (
        CheckConstraint(
            "original_filename = btrim(original_filename) AND original_filename <> ''",
            name="check_file_article_original_filename_not_empty",
        ),
        CheckConstraint(
            "mime_type = btrim(mime_type) AND mime_type <> ''",
            name="check_file_article_mime_type_not_empty",
        ),
        CheckConstraint(
            "file_size_bytes >= 0",
            name="check_file_article_size_nonnegative",
        ),
        {"schema": "public"},
    )

    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("public.users.id"), nullable=False)
    article_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("public.articles.id"), nullable=True)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(255), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
