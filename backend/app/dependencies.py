from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from backend.repositories import article_repository, user_repository
from backend.database.rdb.rdb import get_db
from backend.models.user import User
from backend.services.auth.token_service import (
    TokenExpiredError,
    TokenValidationError,
    verify_access_token,
)

_bearer = HTTPBearer(auto_error=False)      # 헤더가 없어도 오류를 내지 않고 None을 넘긴다 (401을 직접 내기 위해)


def _unauthorized(message: str) -> HTTPException:
    """401 오류를 만든다."""
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=message,
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    """
    Authorization: Bearer <액세스 토큰> 헤더로 지금 요청한 사용자를 찾는다.
    토큰이 없거나, 만료됐거나, 잘못됐거나, 사용자가 없으면 401.
    """
    if credentials is None:
        raise _unauthorized("로그인이 필요합니다.")

    try:
        user_id = verify_access_token(credentials.credentials)
    except TokenExpiredError:
        raise _unauthorized("로그인이 만료되었습니다.")
    except TokenValidationError:
        raise _unauthorized("유효하지 않은 인증 정보입니다.")

    user = db.get(User, user_id)
    if user is None:                        # 토큰은 맞지만 사용자가 없음 (탈퇴 등)
        raise _unauthorized("유효하지 않은 인증 정보입니다.")
    return user


def _not_found() -> HTTPException:
    """404 오류를 만든다."""
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="찾을 수 없습니다.",
    )


def ensure_owner(owner_id: int, user_id: int) -> None:
    """자원의 주인이 지금 사용자가 아니면 404. 남의 자원이 있다는 사실도 숨긴다."""
    if owner_id != user_id:
        raise _not_found()


def ensure_article_access(article_id: int, user_id: int, db: Session) -> None:
    """
    기사가 지금 사용자의 목록(user_articles)에 없으면 404.
    기사는 여러 사용자가 공유하므로 주인 대신 (사용자 ID, 기사 ID) 연결이 있는지 본다.
    """
    if not article_repository.user_has_access(db, user_id, article_id):
        raise _not_found()


def ensure_organization_member(
    organization_id: int,
    user_id: int,
    db: Session,
) -> None:
    user = user_repository.get_by_id(db, user_id)

    if user is None or user.organization_id != organization_id:
        raise _not_found()

def ensure_organization_admin(
    organization_id: int,
    user_id: int,
    db: Session,
) -> None:
    user = user_repository.get_by_id(db, user_id)

    if user is None or user.organization_id != organization_id:
        raise _not_found()

    if user.role != "admin":
        raise _unauthorized("관리자 권한 없습니다.")

def get_current_admin(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    ensure_organization_admin(current_user.organization_id, current_user.id, db)
    return current_user