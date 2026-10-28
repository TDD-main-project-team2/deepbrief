from unittest.mock import MagicMock
import pytest
from datetime import datetime, timedelta, timezone

from backend.schemas.user import UserCreate
from backend.schemas.auth import LoginRequest
from backend.services.auth import auth_service, token_service


def test_register_user_with_valid_organization_code(monkeypatch):
    db = MagicMock()
    organization = MagicMock(id=10)
    monkeypatch.setattr(auth_service.user_repository, "get_by_email", lambda db, email: None)
    monkeypatch.setattr(auth_service.user_repository, "get_organization_by_code", lambda db, code: organization)
    def create_user(db, user):
        db.add(user)
        user.id = 100

    monkeypatch.setattr(auth_service.user_repository, "create", create_user)
    monkeypatch.setattr(
        auth_service,
        "hash_password",
        lambda password: "hashed_password",
    )
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

def test_register_user_with_invalid_organization_code(monkeypatch):
    db = MagicMock()
    monkeypatch.setattr(auth_service.user_repository, "get_by_email", lambda db, email: None)
    monkeypatch.setattr(auth_service.user_repository, "get_organization_by_code", lambda db, code: None)

    data = UserCreate(
        email="reporter@example.com",
        password="test-password",
        nickname="기자",
        organization_code="INVALID-CODE",
    )
    with pytest.raises(auth_service.InvalidOrganizationCodeError):
        auth_service.register_user(db, data)
    db.add.assert_not_called()
    db.commit.assert_not_called()

def test_register_user_with_duplicate_email(monkeypatch):
    db = MagicMock()
    monkeypatch.setattr(auth_service.user_repository, "get_by_email", lambda db, email: MagicMock())
    
    data = UserCreate(email="reporter@example.com", password="test-password", nickname="기자", organization_code="PRESS-001")

    with pytest.raises(auth_service.EmailAlreadyExistsError):
        auth_service.register_user(db, data)
    db.add.assert_not_called()
    db.commit.assert_not_called()    

def test_login_user(monkeypatch):
    db = MagicMock()
    user = MagicMock(id=1, email="reporter@example.com", nickname="기자", password_hash="hashed_password")
    monkeypatch.setattr(auth_service.user_repository, "get_by_email", lambda db, email: user)
    monkeypatch.setattr(auth_service, "verify_password", lambda password, hashed: True)
    result = auth_service.login_user(db, LoginRequest(email="reporter@example.com", password="test-password"))

    assert result is not None
    db.commit.assert_called_once()
    db.rollback.assert_not_called()

def test_login_user_with_wrong_password(monkeypatch):
    db = MagicMock()
    user = MagicMock(id=1, email="reporter@example.com", nickname="기자", password_hash="hashed_password")
    monkeypatch.setattr(auth_service.user_repository, "get_by_email", lambda db, email: user)
    monkeypatch.setattr(auth_service, "verify_password", lambda password, hashed: False)
    with pytest.raises(auth_service.InvalidCredentialsError):
        auth_service.login_user(db, LoginRequest(email="reporter@example.com", password="wrong-password"))
    db.commit.assert_not_called()
    db.rollback.assert_called_once()

def test_login_user_with_nonexistent_email(monkeypatch):
    db = MagicMock()
    monkeypatch.setattr(auth_service.user_repository, "get_by_email", lambda db, email: None)

    with pytest.raises(auth_service.InvalidCredentialsError):
        auth_service.login_user(db, LoginRequest(email="unknown@example.com", password="test-password"))
    db.commit.assert_not_called()

def test_logout_user(monkeypatch):
    db = MagicMock()
    refresh_token = "valid-refresh-token"

    monkeypatch.setattr(auth_service, "delete_refresh_token", lambda token, db: None)

    result = auth_service.logout_user(refresh_token, db)

    assert result is None
    db.commit.assert_called_once()
    db.rollback.assert_not_called()

def test_logout_user_with_invalid_refresh_token(monkeypatch):
    db = MagicMock()
    refresh_token = "invalid-refresh-token"

    def raise_error(token, db):
        raise ValueError("Refresh token not found")

    monkeypatch.setattr(auth_service, "delete_refresh_token", raise_error)

    with pytest.raises(ValueError, match="Refresh token not found"):
        auth_service.logout_user(refresh_token, db)

    db.commit.assert_not_called()
    db.rollback.assert_called_once()

def test_renew_token_pair(monkeypatch):
    db = MagicMock()
    refresh_token = "valid-refresh-token"
    expected_tokens = {"access_token": "new-access-token", "refresh_token": "new-refresh-token"}
    verify_mock = MagicMock(return_value=1)
    delete_mock = MagicMock()
    create_mock = MagicMock(return_value=expected_tokens)

    monkeypatch.setattr(token_service, "_verify_refresh_token", verify_mock)
    monkeypatch.setattr(token_service, "delete_refresh_token", delete_mock)
    monkeypatch.setattr(token_service, "create_token_pair", create_mock)

    result = token_service.renew_token_pair(refresh_token, db)

    assert result == expected_tokens
    verify_mock.assert_called_once_with(refresh_token, db, for_update=True)
    delete_mock.assert_called_once_with(refresh_token, db)
    create_mock.assert_called_once_with(1, db)

def test_renew_token_pair_with_expired_token(monkeypatch):
    db = MagicMock()
    delete_mock = MagicMock()
    create_mock = MagicMock()

    def raise_expired_error(token, db, for_update):
        raise token_service.TokenExpiredError("Refresh token expired")

    monkeypatch.setattr(token_service, "_verify_refresh_token", raise_expired_error)
    monkeypatch.setattr(token_service, "delete_refresh_token", delete_mock)
    monkeypatch.setattr(token_service, "create_token_pair", create_mock)

    with pytest.raises(token_service.TokenExpiredError):
        token_service.renew_token_pair("expired-refresh-token", db)

    delete_mock.assert_not_called()
    create_mock.assert_not_called()

def test_renew_token_pair_with_invalid_token(monkeypatch):
    db = MagicMock()
    delete_mock = MagicMock()
    create_mock = MagicMock()

    def raise_validation_error(token, db, for_update):
        raise token_service.TokenValidationError("Invalid refresh token")

    monkeypatch.setattr(token_service, "_verify_refresh_token", raise_validation_error)
    monkeypatch.setattr(token_service, "delete_refresh_token", delete_mock)
    monkeypatch.setattr(token_service, "create_token_pair", create_mock)

    with pytest.raises(token_service.TokenValidationError):
        token_service.renew_token_pair("invalid-refresh-token", db)

    delete_mock.assert_not_called()
    create_mock.assert_not_called()

def test_create_token_pair(monkeypatch):
    db = MagicMock()
    create_mock = MagicMock()

    monkeypatch.setattr(token_service, "_create_access_token", lambda user_id: "access-token")
    monkeypatch.setattr(token_service, "_create_refresh_token", lambda: "refresh-token")
    monkeypatch.setattr(token_service.refresh_token_repository, "create", create_mock)

    result = token_service.create_token_pair(1, db)

    assert result == {"access_token": "access-token", "refresh_token": "refresh-token"}
    create_mock.assert_called_once()

    args = create_mock.call_args.args
    assert args[:3] == (db, 1, "refresh-token")
    remaining = args[3] - datetime.now(timezone.utc)
    assert timedelta(days=6, hours=23) < remaining < timedelta(days=7)

def test_verify_refresh_token(monkeypatch):
    db = MagicMock()
    record = MagicMock(user_id=1, expired_at=datetime.now(timezone.utc) + timedelta(days=1))
    get_mock = MagicMock(return_value=record)

    monkeypatch.setattr(token_service.refresh_token_repository, "get_by_token", get_mock)

    result = token_service._verify_refresh_token("valid-refresh-token", db)

    assert result == 1
    get_mock.assert_called_once_with(db, "valid-refresh-token", for_update=False)

def test_verify_refresh_token_with_invalid_token(monkeypatch):
    db = MagicMock()
    monkeypatch.setattr(token_service.refresh_token_repository, "get_by_token", lambda *args, **kwargs: None)

    with pytest.raises(token_service.TokenValidationError):
        token_service._verify_refresh_token("invalid-refresh-token", db)

def test_verify_refresh_token_with_expired_token(monkeypatch):
    db = MagicMock()
    record = MagicMock(user_id=1, expired_at=datetime.now(timezone.utc) - timedelta(days=1))
    monkeypatch.setattr(token_service.refresh_token_repository, "get_by_token", lambda *args, **kwargs: record)

    with pytest.raises(token_service.TokenExpiredError):
        token_service._verify_refresh_token("expired-refresh-token", db)

def test_delete_refresh_token(monkeypatch):
    db = MagicMock()
    delete_mock = MagicMock()
    monkeypatch.setattr(token_service.refresh_token_repository, "delete_by_token", delete_mock)

    result = token_service.delete_refresh_token("valid-refresh-token", db)

    assert result is None
    delete_mock.assert_called_once_with(db, "valid-refresh-token")