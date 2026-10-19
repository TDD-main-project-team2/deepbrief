"""회원가입과 로그인 등 사용자 인증 서비스를 제공한다."""

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.models.user import User
from backend.models.organization import Organization
from backend.schemas.auth import LoginRequest, LoginResponse
from backend.schemas.user import UserCreate, UserResponse
from backend.repositories import user_repository
from backend.services.auth.password_service import (
    hash_password,
    verify_password,
)
from backend.services.auth.token_service import (
    create_token_pair,
    delete_refresh_token,
)


class AuthError(ValueError):
    """인증 과정에서 발생하는 오류."""


class EmailAlreadyExistsError(AuthError):
    """이미 등록된 이메일."""


class InvalidCredentialsError(AuthError):
    """이메일 또는 비밀번호가 올바르지 않음."""


class InvalidOrganizationCodeError(AuthError):
    """등록되지 않은 조직 코드."""


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
    try:
        existing_user = user_repository.get_by_email(db, data.email)
        if existing_user is not None:
            raise EmailAlreadyExistsError("이미 사용 중인 이메일입니다.")

        organization = user_repository.get_organization_by_code(db, data.organization_code)
        if organization is None:
            raise InvalidOrganizationCodeError("유효하지 않은 조직 코드입니다.")

        user = User(
            email=str(data.email),
            password_hash=hash_password(data.password),
            nickname=data.nickname,
            organization_id=organization.id,
        )

        user_repository.create(db, user)
        response = UserResponse.model_validate(user)
        db.commit()
        return response

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


def login_user(db: Session, data: LoginRequest) -> LoginResponse:
    try:
        user = user_repository.get_by_email(db, str(data.email))

        if user is None or not verify_password(
            data.password,
            user.password_hash,
        ):
            raise InvalidCredentialsError(
                "이메일 또는 비밀번호가 올바르지 않습니다."
            )

        tokens = create_token_pair(user.id, db)

        result = LoginResponse(
            user=UserResponse.model_validate(user),
            **tokens,
        )
        db.commit()

        return result
    except Exception:
        db.rollback()
        raise


def logout_user(refresh_token: str, db: Session) -> None:
    """리프레시 토큰을 폐기하여 로그아웃한다."""

    try:
        delete_refresh_token(refresh_token, db)
        db.commit()
    except Exception:
        db.rollback()
        raise
