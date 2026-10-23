"""기사 데이터 조회 및 사용자별 기사 연결 Repository."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database.rdb.rdb import SessionLocal
from backend.models.user import User
from backend.models.article import Article
from backend.models.file import File
from backend.models.message import Message
from backend.models.conversation import Conversation
from backend.models.user_article import UserArticle
from backend.models.article_chunk import ArticleChunk

def get_by_content_hash_and_org_id(db: Session, organization_id: int, content_hash: str) -> Article | None:
    return db.query(Article).filter(
        Article.organization_id == organization_id,
        Article.content_hash == content_hash,
    ).first()

def create(db: Session, article: Article) -> Article:
    db.add(article)
    db.flush()
    return article


def save_file(db: Session, file: File) -> File:
    db.add(file)
    db.flush()
    return file


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

def delete_article_association(article_id: int, user_id: int, db: Session) -> bool:
    user_article = db.get(UserArticle, (user_id, article_id))

    if user_article is None:
        return False

    conversation_ids = db.query(Conversation.id).filter(
        Conversation.article_id == article_id,
        Conversation.user_id == user_id
    ).all()
    conversation_ids = [row[0] for row in conversation_ids]

    db.query(Message).filter(
        Message.conversation_id.in_(conversation_ids)
    ).delete(synchronize_session=False)

    db.query(Conversation).filter(
        Conversation.article_id == article_id,
        Conversation.user_id == user_id
    ).delete(synchronize_session=False)

    db.delete(user_article)
    return True

def delete_article_associations(article_id: int, db: Session) -> bool:
    conversation_ids = db.query(Conversation.id).filter(Conversation.article_id == article_id).all()
    conversation_ids = [row[0] for row in conversation_ids]

    if conversation_ids:
        db.query(Message).filter(Message.conversation_id.in_(conversation_ids)).delete(synchronize_session=False)
        db.query(Conversation).filter(Conversation.article_id == article_id).delete(synchronize_session=False)

    db.query(UserArticle).filter(UserArticle.article_id == article_id).delete(synchronize_session=False)
    db.query(ArticleChunk).filter(ArticleChunk.article_id == article_id).delete(synchronize_session=False)
    db.query(File).filter(File.article_id == article_id).delete(synchronize_session=False)

    deleted = db.query(Article).filter(Article.id == article_id).delete(synchronize_session=False)
    return deleted > 0

def update_article(db: Session, article: Article, title: str | None = None, visibility: str | None = None) -> Article:
    """기사 제목 및 공개 범위를 수정한다."""
    if title is not None:
        article.title = title

    if visibility is not None:
        article.visibility = visibility

    db.flush()
    return article


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
    user = db.get(User, user_id)

    if user is None:
        return False

    if user.role == "admin":
        return True

    return db.get(UserArticle, (user_id, article_id)) is not None
