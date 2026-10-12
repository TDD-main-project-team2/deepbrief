from sqlalchemy import BigInteger, Integer, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from pgvector.sqlalchemy import Vector

from backend.models.base import Base

class ArticleChunk(Base):
    __tablename__ = "article_chunks"
    __table_args__ = {"schema": "public"}

    article_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("public.articles.id"), nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(...), nullable=False) # ... -> Embedding모델 결정후 수정
