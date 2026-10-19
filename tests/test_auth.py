from datetime import datetime, timedelta, timezone

import jwt
import pytest
from sqlalchemy import select

from app.core.config import get_settings
from app.models import User


def test_register_success(client):
    r = client.post(
        "/auth/register", json={"email": "Alice@Example.com", "password": "StrongPass123"}
    )
    assert r.status_code == 201
    body = r.json()
    assert body["email"] == "alice@example.com"  # normalized to lowercase
    assert body["role"] == "user"
    assert body["is_active"] is True
    assert "password" not in body and "hashed_password" not in body


def test_register_duplicate_email_conflict(client):
    payload = {"email": "alice@example.com", "password": "StrongPass123"}
    assert client.post("/auth/register", json=payload).status_code == 201
    # Same email, different letter case, still a duplicate.
    r = client.post(
        "/auth/register", json={"email": "ALICE@example.com", "password": "StrongPass123"}
    )
    assert r.status_code == 409


@pytest.mark.parametrize(
    "payload",
    [
        {"email": "not-an-email", "password": "StrongPass123"},
        {"email": "a@example.com", "password": "short"},
        {"email": "a@example.com", "password": "x" * 73},
        {"email": "a@example.com"},
        {},
    ],
)
def test_register_validation_errors(client, payload):
    assert client.post("/auth/register", json=payload).status_code == 422


def test_register_cannot_choose_role(client):
    """Mass-assignment guard: a client-supplied role must be ignored."""
    r = client.post(
        "/auth/register",
        json={"email": "evil@example.com", "password": "StrongPass123", "role": "admin"},
    )
    assert r.status_code == 201
    assert r.json()["role"] == "user"


def test_login_success_returns_bearer_token(client):
    client.post(
        "/auth/register", json={"email": "alice@example.com", "password": "StrongPass123"}
    )
    r = client.post(
        "/auth/login", data={"username": "alice@example.com", "password": "StrongPass123"}
    )
    assert r.status_code == 200
    assert r.json()["token_type"] == "bearer"
    assert r.json()["access_token"]


def test_login_wrong_password_and_unknown_email_look_identical(client):
    client.post(
        "/auth/register", json={"email": "alice@example.com", "password": "StrongPass123"}
    )
    wrong_pw = client.post(
        "/auth/login", data={"username": "alice@example.com", "password": "nope-nope-nope"}
    )
    unknown = client.post(
        "/auth/login", data={"username": "ghost@example.com", "password": "StrongPass123"}
    )
    assert wrong_pw.status_code == unknown.status_code == 401
    # Anti user-enumeration: the response must not reveal which case it was.
    assert wrong_pw.json() == unknown.json()


def test_me_with_valid_token(client, auth_headers):
    r = client.get("/users/me", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["email"] == "alice@example.com"


def test_me_without_token(client):
    r = client.get("/users/me")
    assert r.status_code == 401


def test_me_with_garbage_token(client):
    r = client.get("/users/me", headers={"Authorization": "Bearer not.a.jwt"})
    assert r.status_code == 401


def test_me_with_expired_token(client):
    s = get_settings()
    expired = jwt.encode(
        {"sub": "1", "exp": datetime.now(timezone.utc) - timedelta(minutes=1)},
        s.secret_key,
        algorithm=s.jwt_algorithm,
    )
    r = client.get("/users/me", headers={"Authorization": f"Bearer {expired}"})
    assert r.status_code == 401


def test_me_with_token_signed_by_wrong_secret(client, auth_headers):
    forged = jwt.encode(
        {"sub": "1", "exp": datetime.now(timezone.utc) + timedelta(minutes=5)},
        "attacker-guess-that-is-long-enough-for-hs256",
        algorithm="HS256",
    )
    r = client.get("/users/me", headers={"Authorization": f"Bearer {forged}"})
    assert r.status_code == 401


def test_inactive_user_is_blocked(client, db_session, auth_headers):
    user = db_session.scalar(select(User).where(User.email == "alice@example.com"))
    user.is_active = False
    db_session.commit()

    # Existing token no longer works...
    assert client.get("/users/me", headers=auth_headers).status_code == 403
    # ...and a fresh login is refused too.
    r = client.post(
        "/auth/login", data={"username": "alice@example.com", "password": "StrongPass123"}
    )
    assert r.status_code == 403