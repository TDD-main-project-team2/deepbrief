from unittest.mock import MagicMock

import pytest

from backend.schemas.user import UserCreate
from backend.services.auth import auth_service


def test_register_user_with_valid_organization_code(monkeypatch):
    """유효한 조직코드로 회원가입하면 조직 ID가 연결된다."""
    db = MagicMock()
    organization = MagicMock()
    organization.id = 10

    # 기존 이메일 없음 → 조직코드 조회 성공
    db.scalar.side_effect = [None, organization]

    # 실제 비밀번호 해싱은 실행하지 않음
    monkeypatch.setattr(
        auth_service,
        "hash_password",
        lambda password: "hashed_password",
    )

    # DB가 자동 생성하는 사용자 ID를 모의 처리
    db.refresh.side_effect = lambda user: setattr(user, "id", 100)

    data = UserCreate(
        email="reporter@example.com",
        password="test-password",
        nickname="기자",
        organization_code="PRESS-001",
    )

    result = auth_service.register_user(db, data)

    assert result.id == 100
    assert result.email == "reporter@example.com"

    created_user = db.add.call_args.args[0]
    assert created_user.organization_id == 10
    assert created_user.password_hash == "hashed_password"

    db.commit.assert_called_once()


def test_register_user_with_invalid_organization_code():
    """잘못된 조직코드면 회원가입을 거부한다."""
    db = MagicMock()

    # 기존 이메일 없음 → 해당 조직코드도 없음
    db.scalar.side_effect = [None, None]

    data = UserCreate(
        email="reporter@example.com",
        password="test-password",
        nickname="기자",
        organization_code="INVALID-CODE",
    )

    with pytest.raises(auth_service.InvalidOrganizationCodeError):
        auth_service.register_user(db, data)

    # 사용자 저장이나 커밋이 일어나면 안 됨
    db.add.assert_not_called()
    db.commit.assert_not_called()
