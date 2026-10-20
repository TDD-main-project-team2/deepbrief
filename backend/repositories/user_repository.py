from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.organization import Organization
from backend.models.user import User
from backend.models.user_article import UserArticle


def get_by_id(db: Session, user_id: int) -> User | None:
    return db.get(User, user_id)


def get_by_article_id(db: Session, article_id: int) -> User | None:
    return db.scalar(
        select(User)
        .join(UserArticle, UserArticle.user_id == User.id)
        .where(UserArticle.article_id == article_id)
    )


def get_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email))


def get_organization_by_code(db: Session, code: str) -> Organization | None:
    return db.scalar(select(Organization).where(Organization.code == code))


def create(db: Session, user: User) -> User:
    db.add(user)
    db.flush()
    db.refresh(user)
    return user