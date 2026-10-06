from sqlalchemy import BigInteger, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base

class FileArticle(Base):
    __tablename__ = "file_articles"
    __table_args__ = {"schema": "public"}

    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("public.users.id"), nullable=False)
    article_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("public.articles.id"), nullable=True)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(255), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
