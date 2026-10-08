import os
import secrets
from datetime import datetime, timedelta, timezone
from hashlib import sha256

import jwt
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.refresh_token import RefreshToken


class TokenValidationError(ValueError):
    """토큰이 유효하지 않을 때 발생한다."""


class TokenExpiredError(TokenValidationError):
    """토큰이 만료됐을 때 발생한다."""


def create_token_pair(user_id: int, db: Session) -> dict[str, str]:
    """인증된 사용자의 토큰을 발급한다. 호출자가 트랜잭션을 커밋해야 한다."""

    access_token = _create_access_token(user_id)
    refresh_token = _create_refresh_token()

    db.add(
        RefreshToken(
            user_id=user_id,
            token_hash=sha256(refresh_token.encode("utf-8")).hexdigest(),
            expired_at=datetime.now(timezone.utc) + timedelta(days=7),
        )
    )
    db.flush()

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
    }


def _create_access_token(user_id: int) -> str:
    """사용자 ID를 문자열 sub로 담은 액세스 토큰을 생성한다."""

    secret_key = os.getenv("JWT_SECRET_KEY")
    if not secret_key:
        raise RuntimeError("JWT_SECRET_KEY 환경변수를 설정해주세요.")

    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(minutes=15),
        "type": "access",
    }
    return jwt.encode(payload, secret_key, algorithm="HS256")


def verify_access_token(token: str) -> int:
    """액세스 토큰을 검증하고 사용자 ID를 반환한다."""

    secret_key = os.getenv("JWT_SECRET_KEY")
    if not secret_key:
        raise RuntimeError("JWT_SECRET_KEY 환경변수를 설정해주세요.")
    if not isinstance(token, str) or not token:
        raise TokenValidationError("액세스 토큰이 없습니다.")

    try:
        payload = jwt.decode(
            token,
            secret_key,
            algorithms=["HS256"],
            options={"require": ["sub", "iat", "exp", "type"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise TokenExpiredError("액세스 토큰이 만료됐습니다.") from exc
    except jwt.InvalidTokenError as exc:
        raise TokenValidationError("유효하지 않은 액세스 토큰입니다.") from exc

    type = payload["type"]
    if type != "access":
        raise TokenValidationError("액세스 토큰이 아닙니다.")

    sub = payload["sub"]
    try:
        user_id = int(sub)
    except (KeyError, TypeError, ValueError) as exc:
        raise TokenValidationError(
            "액세스 토큰의 사용자 ID(sub)가 없거나 정수로 변환할 수 없습니다. "
        ) from exc

    return user_id


def _create_refresh_token() -> str:
    """암호학적 난수로 리프레시 토큰 원본을 생성한다."""

    return secrets.token_urlsafe(32)


def _verify_refresh_token(refresh_token: str, db: Session) -> int:
    """토큰 해시로 DB 기록을 조회하고 만료·폐기 여부를 검증한 뒤 사용자 ID를 반환한다."""

    if not isinstance(refresh_token, str) or not refresh_token:
        raise TokenValidationError("리프레시 토큰이 없습니다.")

    token_hash = sha256(refresh_token.encode("utf-8")).hexdigest()
    record = db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    ).scalar_one_or_none()

    if record is None:
        raise TokenValidationError("유효하지 않거나 폐기된 리프레시 토큰입니다.")
    if record.expired_at <= datetime.now(timezone.utc):
        raise TokenExpiredError("리프레시 토큰이 만료됐습니다.")
        
    return record.user_id


def renew_token_pair(refresh_token: str, db: Session) -> dict[str, str]:
    """리프레시 토큰을 검증하고 기존 토큰 폐기와 새 토큰 저장을 원자적으로 처리한다."""
    pass


def revoke_refresh_token(refresh_token: str, db: Session) -> None:
    """로그아웃 시 해당 리프레시 토큰을 폐기한다."""
    pass


def delete_expired_refresh_tokens(db: Session) -> int:
    """만료된 리프레시 토큰 기록을 삭제하고 삭제 건수를 반환한다."""
    pass
