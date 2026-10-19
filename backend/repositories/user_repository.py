from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.organization import Organization
from backend.models.user import User


def get_by_id(db: Session, user_id: int) -> User | None:
    return db.get(User, user_id)

def get_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email))


def get_organization_by_code(db: Session, code: str) -> Organization | None:
    return db.scalar(select(Organization).where(Organization.code == code))


def create(db: Session, user: User) -> User:
    db.add(user)
    db.flush()
    db.refresh(user)
    return user