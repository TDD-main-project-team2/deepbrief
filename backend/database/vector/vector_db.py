from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.models.article import Article
from backend.models.article_chunk import ArticleChunk
from backend.models.user_article import UserArticle
from backend.models.user import User
import os

from dotenv import load_dotenv
load_dotenv()

class VectorDB:
    def __init__(self):
        db_url = os.getenv("DATABASE_URL")
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

    def search_similar_chunks(self, query, embedding: list[float], top_k: int = 5) -> list[ArticleChunk]:
        return query.order_by(ArticleChunk.embedding.cosine_distance(embedding)).limit(top_k).all()

    def search_article_chunks(self, embedding: list[float], article_id: int, top_k: int = 5):
        with self.SessionLocal() as session:
            query = session.query(ArticleChunk).filter(ArticleChunk.article_id == article_id)
            return self.search_similar_chunks(query, embedding, top_k)

    def search_organization_chunks(self, embedding: list[float], article_id: int, top_k: int = 5):
        with self.SessionLocal() as session:
            organization_id = (
                session.query(User.organization_id)
                .join(UserArticle, UserArticle.user_id == User.id)
                .filter(UserArticle.article_id == article_id)
                .distinct()
                .scalar()
            )

            if organization_id is None:
                raise ValueError("기사에 연결된 조직을 찾을 수 없습니다.")
        
            query = (
                session.query(ArticleChunk)
                .join(Article, Article.id == ArticleChunk.article_id)
                .join(UserArticle, UserArticle.article_id == Article.id)
                .join(User, User.id == UserArticle.user_id)
                .filter(
                    User.organization_id == organization_id,
                    ArticleChunk.article_id != article_id,
                )
            )
            return self.search_similar_chunks(query, embedding, top_k)

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

    def replace_article_chunks(self, article_id: int, chunks: list[ArticleChunk]):
        """해당 기사의 기존 청크를 새 청크로 교체한다.

        Args:
            article_id (int): 청크를 교체할 기사의 기본키.
            chunks (list[ArticleChunk]): 원문과 임베딩 벡터를 담은 새 청크 목록.

        Notes:
            삭제와 저장을 함께 커밋하며 실패 시 자동으로 롤백한다.
            기사 행을 잠가 같은 기사의 동시 교체를 순서대로 처리한다.
        """
        
        with self.SessionLocal.begin() as session:
            session.query(Article).filter(Article.id == article_id).with_for_update().one()
            session.query(ArticleChunk).filter(
                ArticleChunk.article_id == article_id
            ).delete(synchronize_session=False)
            session.add_all(chunks)

vector_db = VectorDB()