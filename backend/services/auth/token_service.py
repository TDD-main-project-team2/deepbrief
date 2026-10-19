import os
import secrets
from datetime import datetime, timedelta, timezone
from hashlib import sha256

import jwt
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from backend.models.refresh_token import RefreshToken


class TokenValidationError(ValueError):
    """토큰이 유효하지 않을 때 발생한다."""


class TokenExpiredError(TokenValidationError):
    """토큰이 만료됐을 때 발생한다."""


def create_token_pair(user_id: int, db: Session) -> dict[str, str]:
    """리프레시/액세스 토큰을 발급하고 리프레시 토큰 해시를 DB에 저장한다.

    Args:
        user_id (int): 로그인 인증에 성공한 사용자의 DB 기본키.
        db (Session): 리프레시 토큰 기록을 저장할 DB 세션.

    Returns:
        dict[str, str]: access_token은 액세스 토큰 JWT 문자열, 
        refresh_token은 리프레시 토큰 원본 문자열인 딕셔너리.

    Raises:
        RuntimeError: JWT_SECRET_KEY 환경변수가 설정되지 않은 경우.
        SQLAlchemyError: 리프레시 토큰 기록 저장에 실패한 경우.

    Notes:
        리프레시 토큰의 DB 만료 시각은 발급 시각으로부터 7일이다.
        호출자가 성공 시 commit(), 실패 시 rollback()을 수행해야 한다.
    """

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
    """액세스 토큰을 생성한다.

    Args:
        user_id (int): 액세스 토큰의 sub에 문자열로 저장할 DB 사용자 ID.

    Returns:
        str: HS256으로 서명한 유효기간 15분의 액세스 토큰 JWT 문자열.

    Raises:
        RuntimeError: JWT_SECRET_KEY 환경변수가 설정되지 않은 경우.
    """

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


def _create_refresh_token() -> str:
    """리프레시 토큰(원본)을 생성한다.

    Args:
        None

    Returns:
        str: 32바이트 난수를 URL-safe 형식으로 인코딩한 리프레시 토큰 원본.

    Raises:
        None

    Notes:
        리프레시 토큰 해시와 만료 시각은 발급 함수에서 DB에 저장한다.
    """

    return secrets.token_urlsafe(32)


def verify_access_token(token: str) -> int:
    """액세스 토큰을 검증한다.

    Args:
        token (str): 클라이언트가 전달한 액세스 토큰 JWT 문자열.

    Returns:
        int: 액세스 토큰의 sub에서 추출한 DB 사용자 ID.

    Raises:
        RuntimeError: JWT_SECRET_KEY 환경변수가 설정되지 않은 경우.
        TokenExpiredError: 액세스 토큰이 만료된 경우.
        TokenValidationError: 액세스 토큰이 없거나 서명, 형식, 필수 정보,
            종류 또는 사용자 ID가 유효하지 않은 경우.

    Notes:
        반환된 DB 사용자 ID의 실제 존재 여부는 별도로 확인해야 한다.
    """

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


def _verify_refresh_token(
    refresh_token: str, db: Session, *, for_update: bool = False
) -> int:
    """리프레시 토큰을 검증한다.

    Args:
        refresh_token (str): 클라이언트가 전달한 리프레시 토큰 원본 문자열.
        db (Session): 리프레시 토큰 기록을 조회할 DB 세션.
        for_update (bool): True이면 조회할 DB 기록에 행 잠금을 적용한다.
            기본값은 False이며, 키워드 인자로만 전달한다.

    Returns:
        int: 리프레시 토큰 DB 기록에 저장된 사용자 ID.

    Raises:
        TokenExpiredError: 리프레시 토큰의 DB 만료 시각이 지난 경우.
        TokenValidationError: 리프레시 토큰이 없거나 일치하는 DB 기록이 없는 경우.
        SQLAlchemyError: DB 조회에 실패하거나 일치하는 기록이 여러 개인 경우.

    Notes:
        리프레시 토큰 폐기는 DB 기록 삭제로 처리한다.
        행 잠금은 호출자의 트랜잭션이 끝날 때까지 유지된다.
    """

    if not isinstance(refresh_token, str) or not refresh_token:
        raise TokenValidationError("리프레시 토큰이 없습니다.")

    token_hash = sha256(refresh_token.encode("utf-8")).hexdigest()
    query = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    if for_update:
        query = query.with_for_update()
    record = db.execute(query).scalar_one_or_none()

    if record is None:
        raise TokenValidationError("유효하지 않거나 폐기된 리프레시 토큰입니다.")
    if record.expired_at <= datetime.now(timezone.utc):
        raise TokenExpiredError("리프레시 토큰이 만료됐습니다.")
        
    return record.user_id


def renew_token_pair(refresh_token: str, db: Session) -> dict[str, str]:
    """리프레시 토큰을 검증하고 새로운 리프레시/액세스 토큰으로 교체한다.

    Args:
        refresh_token (str): 갱신에 사용할 리프레시 토큰 원본 문자열.
        db (Session): 기존 리프레시 토큰 삭제와 새 기록 저장에 사용할 DB 세션.

    Returns:
        dict[str, str]: 새로운 access_token JWT 문자열과 refresh_token 원본 문자열을 담은 딕셔너리.

    Raises:
        TokenExpiredError: 기존 리프레시 토큰이 만료된 경우.
        TokenValidationError: 기존 리프레시 토큰이 없거나 유효하지 않은 경우.
        RuntimeError: JWT_SECRET_KEY 환경변수가 설정되지 않은 경우.
        SQLAlchemyError: 리프레시 토큰 조회, 삭제 또는 저장에 실패한 경우.

    Notes:
        기존 리프레시 토큰 기록을 잠근 뒤 삭제하고 새 기록을 저장한다.
        성공 시 commit(), 실패 시 rollback()으로 갱신 트랜잭션을 마무리한다.
        새로운 리프레시/액세스 토큰은 커밋 성공 후 클라이언트에 전달한다.
    """

    try:
        user_id = _verify_refresh_token(refresh_token, db, for_update=True)
        delete_refresh_token(refresh_token, db)
        tokens = create_token_pair(user_id, db)
        db.commit()
        return tokens
    except Exception:
        db.rollback()
        raise


def delete_refresh_token(refresh_token: str, db: Session) -> None:
    """특정 리프레시 토큰의 DB 기록을 삭제한다.

    Args:
        refresh_token (str): 삭제할 리프레시 토큰 원본 문자열.
        db (Session): 리프레시 토큰 기록을 삭제할 DB 세션.

    Returns:
        None

    Raises:
        TokenValidationError: 리프레시 토큰이 없거나 문자열이 아닌 경우.
        SQLAlchemyError: 리프레시 토큰 기록 삭제에 실패한 경우.

    Notes:
        일치하는 기록이 없어도 정상 종료한다.
        호출자가 성공 시 commit(), 실패 시 rollback()을 수행해야 한다.
    """

    if not isinstance(refresh_token, str) or not refresh_token:
        raise TokenValidationError("리프레시 토큰이 없습니다.")

    token_hash = sha256(refresh_token.encode("utf-8")).hexdigest()
    db.execute(delete(RefreshToken).where(RefreshToken.token_hash == token_hash))


def delete_expired_refresh_tokens(db: Session) -> int:
    """현재 시각에 만료된 리프레시 토큰의 DB 기록을 모두 삭제한다.
    -> 서버의 주기적인 정리 작업에 사용

    Args:
        db (Session): 만료된 리프레시 토큰 기록을 삭제할 DB 세션.

    Returns:
        int: 삭제된 리프레시 토큰 기록 수. 삭제 대상이 없으면 0.

    Raises:
        SQLAlchemyError: 만료된 리프레시 토큰 기록 삭제에 실패한 경우.

    Notes:
        호출자가 성공 시 commit(), 실패 시 rollback()을 수행해야 한다.
    """

    result = db.execute(
        delete(RefreshToken).where(
            RefreshToken.expired_at <= datetime.now(timezone.utc)
        )
    )

    return result.rowcount
