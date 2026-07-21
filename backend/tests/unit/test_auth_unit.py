# backend/tests/unit/test_auth_unit.py
import pytest
from app.core.security import verify_password, get_password_hash, create_access_token, create_refresh_token, decode_token
from app.core.config import settings

def test_password_hashing():
    """Unit test: Password hashing and bcrypt verification."""
    password = "MySecurePassword123!"
    hashed = get_password_hash(password)

    assert hashed != password
    assert verify_password(password, hashed) is True
    assert verify_password("WrongPassword", hashed) is False

def test_jwt_access_token_creation_and_decoding():
    """Unit test: Access token creation and payload extraction."""
    subject = "user_12345"
    role = "Owner"
    token = create_access_token(subject=subject, role=role)

    payload = decode_token(token, settings.JWT_SECRET)
    assert payload["sub"] == subject
    assert payload["role"] == role
    assert payload["type"] == "access"

def test_jwt_refresh_token_type():
    """Unit test: Refresh token creation marked with refresh type."""
    subject = "user_67890"
    token = create_refresh_token(subject=subject)

    payload = decode_token(token, settings.JWT_REFRESH_SECRET)
    assert payload["sub"] == subject
    assert payload["type"] == "refresh"
