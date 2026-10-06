from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models.article_chunk import ArticleChunk
import os

class VectorDB:
    def __init__(self):
        db_url = os.getenv("DB_URL")
        self.engine = create_engine(db_url)
        self.SessionLocal = sessionmaker(bind=self.engine)

    def add_chunk(self, chunk: ArticleChunk):
        with self.SessionLocal() as session:
            session.add(chunk)
            session.commit()

    def add_chunks(self, chunks: list[ArticleChunk]):
        with self.SessionLocal() as session:
            for chunk in chunks:
                session.add(chunk)
            session.commit()

    def search_similar_chunks(self, embedding: list[float], top_k: int = 5):
        with self.SessionLocal() as session:
            query = (
                session.query(ArticleChunk)
                .order_by(ArticleChunk.embedding.cosine_distance(embedding))
                .limit(top_k)
            )
            return query.all()

    def delete_article_chunks(self, article_id: int):
        with self.SessionLocal() as session:
            session.query(ArticleChunk).filter(
                ArticleChunk.article_id == article_id
            ).delete()
            session.commit()

    def get_article_chunks(self, article_id: int):  
        with self.SessionLocal() as session:
            return (
                session.query(ArticleChunk)
                .filter(ArticleChunk.article_id == article_id)
                .order_by(ArticleChunk.chunk_index)
                .all()
            )