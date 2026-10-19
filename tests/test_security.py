from datetime import datetime, timedelta, timezone

import jwt
import pytest

from app.core.config import get_settings
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_password_is_hashed_and_verifiable():
    hashed = hash_password("StrongPass123")
    assert hashed != "StrongPass123"
    assert verify_password("StrongPass123", hashed)
    assert not verify_password("wrong-password", hashed)


def test_same_password_gets_different_hashes():
    # Random salt per hash: equal passwords must not produce equal hashes.
    assert hash_password("StrongPass123") != hash_password("StrongPass123")


def test_token_roundtrip():
    token = create_access_token(42)
    assert decode_access_token(token)["sub"] == "42"


def test_expired_token_is_rejected():
    s = get_settings()
    expired = jwt.encode(
        {"sub": "1", "exp": datetime.now(timezone.utc) - timedelta(minutes=1)},
        s.secret_key,
        algorithm=s.jwt_algorithm,
    )
    with pytest.raises(jwt.ExpiredSignatureError):
        decode_access_token(expired)