from unittest.mock import MagicMock
import pytest

from backend.schemas.user import UserCreate
from backend.schemas.auth import LoginRequest
from backend.services.auth import auth_service, token_service
from backend.models.organization import Organization


def test_register_user_with_valid_organization_code(monkeypatch):
    db = MagicMock()
    organization = MagicMock(id=10)
    db.scalar.side_effect = [None, organization]
    db.refresh.side_effect = lambda user: setattr(user, "id", 100)

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

def test_register_user_with_invalid_organization_code():
    db = MagicMock()
    db.scalar.side_effect = [None, None]

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

def test_register_user_with_duplicate_email():
    db = MagicMock()
    db.scalar.return_value = MagicMock()

    data = UserCreate(email="reporter@example.com", password="test-password", nickname="기자", organization_code="PRESS-001")

    with pytest.raises(auth_service.EmailAlreadyExistsError):
        auth_service.register_user(db, data)
    db.add.assert_not_called()
    db.commit.assert_not_called()    

def test_login_user(monkeypatch):
    db = MagicMock()
    user = MagicMock(id=1, email="reporter@example.com", nickname="기자", password_hash="hashed_password")
    db.scalar.return_value = user

    monkeypatch.setattr(auth_service, "verify_password", lambda password, hashed: True)

    result = auth_service.login_user(db, LoginRequest(email="reporter@example.com", password="test-password"))

    assert result is not None

def test_login_user_with_wrong_password(monkeypatch):
    db = MagicMock()
    user = MagicMock(id=1, email="reporter@example.com", nickname="기자", password_hash="hashed_password")
    db.scalar.return_value = user

    monkeypatch.setattr(auth_service, "verify_password", lambda password, hashed: False)

    with pytest.raises(auth_service.InvalidCredentialsError):
        auth_service.login_user(db, LoginRequest(email="reporter@example.com", password="wrong-password"))

def test_login_user_with_nonexistent_email():
    db = MagicMock()
    db.scalar.return_value = None

    with pytest.raises(auth_service.InvalidCredentialsError):
        auth_service.login_user(db, LoginRequest(email="unknown@example.com", password="test-password"))

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

    monkeypatch.setattr(token_service, "_verify_refresh_token", lambda token, db, for_update: 1)
    monkeypatch.setattr(token_service, "delete_refresh_token", lambda token, db: None)
    monkeypatch.setattr(token_service, "create_token_pair", lambda user_id, db: expected_tokens)

    result = token_service.renew_token_pair(refresh_token, db)

    assert result == expected_tokens

def test_renew_token_pair_with_expired_token(monkeypatch):
    db = MagicMock()

    def raise_expired_error(token, db, for_update):
        raise token_service.TokenExpiredError("Refresh token expired")

    monkeypatch.setattr(token_service, "_verify_refresh_token", raise_expired_error)

    with pytest.raises(token_service.TokenExpiredError):
        token_service.renew_token_pair("expired-refresh-token", db)

    token_service.delete_refresh_token
    db.commit.assert_not_called()

def test_renew_token_pair_with_invalid_token(monkeypatch):
    db = MagicMock()

    def raise_validation_error(token, db, for_update):
        raise token_service.TokenValidationError("Invalid refresh token")

    monkeypatch.setattr(token_service, "_verify_refresh_token", raise_validation_error)

    with pytest.raises(token_service.TokenValidationError):
        token_service.renew_token_pair("invalid-refresh-token", db)