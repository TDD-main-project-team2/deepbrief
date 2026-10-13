
"""회원가입과 로그인 등 사용자 인증 서비스를 제공한다."""

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.models.user import User
from backend.schemas.auth import LoginRequest
from backend.schemas.user import UserCreate, UserResponse
from backend.services.auth.password_service import (
    hash_password,
    verify_password,
)
from backend.services.auth.token_service import create_token_pair


class AuthError(ValueError):
    """인증 과정에서 발생하는 오류."""


class EmailAlreadyExistsError(AuthError):
    """이미 등록된 이메일."""


class InvalidCredentialsError(AuthError):
    """이메일 또는 비밀번호가 올바르지 않음."""


def _is_email_unique_violation(exc: IntegrityError) -> bool:
    """PostgreSQL에서 이메일 UNIQUE 제약조건 위반인지 확인한다."""
    original_error = exc.orig
    sqlstate = getattr(original_error, "sqlstate", None)
    if sqlstate is None:
        sqlstate = getattr(original_error, "pgcode", None)

    diagnostic = getattr(original_error, "diag", None)
    constraint_name = getattr(diagnostic, "constraint_name", None)

    return (
        sqlstate == "23505"
        and constraint_name in {"users_email_key", "uq_users_email", "unique_users_email",}
    )


def register_user(db: Session, data: UserCreate) -> UserResponse:
    """신규 사용자를 등록한다."""

    try:
        existing_user = db.scalar(
            select(User).where(User.email == str(data.email))
        )
        if existing_user is not None:
            raise EmailAlreadyExistsError("이미 사용 중인 이메일입니다.")

        user = User(
            email=str(data.email),
            password_hash=hash_password(data.password),
            nickname=data.nickname,
        )

        db.add(user)
        db.commit()
        db.refresh(user)

        return UserResponse.model_validate(user)

    except IntegrityError as exc:
        db.rollback()

        if _is_email_unique_violation(exc):
            raise EmailAlreadyExistsError(
                "이미 사용 중인 이메일입니다."
            ) from exc

        raise
    except Exception:
        db.rollback()
        raise


def login_user(db: Session, data: LoginRequest) -> dict[str, object]:
    """이메일과 비밀번호를 검증하고 토큰을 발급한다."""

    try:
        user = db.scalar(
            select(User).where(User.email == str(data.email))
        )

        if user is None or not verify_password(
            data.password,
            user.password_hash,
        ):
            raise InvalidCredentialsError(
                "이메일 또는 비밀번호가 올바르지 않습니다."
            )

        tokens = create_token_pair(user.id, db)
        db.commit()

        return {
            "user": UserResponse.model_validate(user),
            **tokens,
        }

    except Exception:
        db.rollback()
        raise
