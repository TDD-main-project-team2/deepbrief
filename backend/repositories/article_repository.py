"""기사 데이터 조회 및 사용자별 기사 연결 Repository."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database.rdb.rdb import SessionLocal
from backend.models.user import User
from backend.models.article import Article
from backend.models.conversation import Conversation
from backend.models.user_article import UserArticle

def get_by_content_hash(db: Session, content_hash: str) -> Article | None:
    return db.query(Article).filter(Article.content_hash == content_hash).first()

def create(db: Session, article: Article) -> Article:
    db.add(article)
    db.commit()
    db.refresh(article)
    return article

def find_article_by_id(article_id: int) -> Article | None:
    """기사 ID로 기사를 조회한다."""
    with SessionLocal() as db:
        return db.get(Article, article_id)


def find_all_by_user(user_id: int) -> list[Article]:
    """사용자와 연결된 기사 목록을 조회한다."""
    with SessionLocal() as db:
        return list(
            db.scalars(
                select(Article)
                .join(UserArticle, UserArticle.article_id == Article.id)
                .where(UserArticle.user_id == user_id)
                .order_by(Article.id.asc())
            ).all()
        )


def find_all_by_org(db: Session, organization_id: int) -> list[Article]:
    return db.scalars(
        select(Article)
        .join(UserArticle, UserArticle.article_id == Article.id)
        .join(User, User.id == UserArticle.user_id)
        .where(User.organization_id == organization_id)
        .distinct()
    ).all()


def find_all_public_by_org(db: Session, organization_id: int) -> list[Article]:
    return db.scalars(
        select(Article)
        .join(UserArticle, UserArticle.article_id == Article.id)
        .join(User, User.id == UserArticle.user_id)
        .where(
            User.organization_id == organization_id,
            Article.visibility == "public",
        )
        .distinct()
    ).all()


def find_article_by_conversation_id(
    conversation_id: int,
) -> Article | None:
    """대화 ID에 연결된 기사를 조회한다."""
    with SessionLocal() as db:
        return db.scalar(
            select(Article)
            .join(Conversation, Conversation.article_id == Article.id)
            .where(Conversation.id == conversation_id)
        )


def delete_article(article_id: int, user_id: int) -> bool:
    """사용자와 기사의 연결만 삭제한다.

    기사 본문은 다른 사용자도 사용할 수 있으므로 삭제하지 않는다.
    연결이 없으면 False를 반환한다.
    """
    with SessionLocal() as db:
        user_article = db.get(UserArticle, (user_id, article_id))

        if user_article is None:
            return False

        db.delete(user_article)
        db.commit()
        return True


def update_category(article_id: int, category: str) -> None:
    """기사의 카테고리를 갱신한다."""
    with SessionLocal() as db:
        article = db.get(Article, article_id)

        if article is None:
            return

        article.category = category
        db.commit()


def add_article_to_user(user_id: int, article_id: int) -> None:
    """사용자와 기사의 연결을 등록한다."""
    with SessionLocal() as db:
        user_article = db.get(UserArticle, (user_id, article_id))

        if user_article is not None:
            return

        db.add(
            UserArticle(
                user_id=user_id,
                article_id=article_id,
            )
        )
        db.commit()

def user_has_access(db: Session, user_id: int, article_id: int) -> bool:
    return db.get(UserArticle, (user_id, article_id)) is not None