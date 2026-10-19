from datetime import datetime, timezone
from hashlib import sha256

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from backend.models.refresh_token import RefreshToken


def create(db: Session, user_id: int, token: str, expired_at: datetime) -> RefreshToken:
    record = RefreshToken(
        user_id=user_id,
        token_hash=sha256(token.encode("utf-8")).hexdigest(),
        expired_at=expired_at,
    )
    db.add(record)
    db.flush()
    return record


def get_by_token(db: Session, token: str, *, for_update: bool = False) -> RefreshToken | None:
    token_hash = sha256(token.encode("utf-8")).hexdigest()
    query = select(RefreshToken).where(RefreshToken.token_hash == token_hash)

    if for_update:
        query = query.with_for_update()

    return db.execute(query).scalar_one_or_none()


def delete_by_token(db: Session, token: str) -> None:
    token_hash = sha256(token.encode("utf-8")).hexdigest()
    db.execute(delete(RefreshToken).where(RefreshToken.token_hash == token_hash))


def delete_expired(db: Session) -> int:
    result = db.execute(delete(RefreshToken).where(RefreshToken.expired_at <= datetime.now(timezone.utc)))
    return result.rowcount or 0