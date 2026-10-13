from sqlalchemy import BigInteger, Integer, Text, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from pgvector.sqlalchemy import Vector

from backend.models.base import Base

class ArticleChunk(Base):
    __tablename__ = "article_chunks"
    __table_args__ = (
        UniqueConstraint(
            "article_id",
            "chunk_index",
            name="uq_article_chunks_article_id_chunk_index", 
        ),
        {"schema": "public"}
    )

    article_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("public.articles.id"), nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(1024), nullable=False) 
