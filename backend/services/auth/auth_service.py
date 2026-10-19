"""회원가입과 로그인 등 사용자 인증 서비스를 제공한다."""

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.models.user import User
from backend.models.organization import Organization
from backend.schemas.auth import LoginRequest, LoginResponse
from backend.schemas.user import UserCreate, UserResponse
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
    """신규 사용자를 등록한다."""

    try:
        existing_user = db.scalar(
            select(User).where(User.email == str(data.email))
        )
        if existing_user is not None:
            raise EmailAlreadyExistsError("이미 사용 중인 이메일입니다.")

        organization = db.scalar(
            select(Organization).where(
            Organization.code == data.organization_code
            )
        )

        if organization is None:
            raise InvalidOrganizationCodeError("유효하지 않은 조직 코드입니다.")

        user = User(
            email=str(data.email),
            password_hash=hash_password(data.password),
            nickname=data.nickname,
            organization_id=organization.id,
        )

        db.add(user)

        # INSERT를 실행하고 DB에서 생성된 ID를 확보한다.
        db.flush()
        db.refresh(user)

        # 커밋 전에 응답 객체를 생성한다.
        response = UserResponse.model_validate(user)

        # 모든 준비가 성공한 경우에만 최종 반영한다.
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

        # DB 커밋 전에 응답 데이터를 준비한다.
        result = LoginResponse(
            user=UserResponse.model_validate(user),
            **tokens,
        )

        # 응답 데이터 준비까지 성공한 뒤 DB 변경 사항을 확정한다.
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
