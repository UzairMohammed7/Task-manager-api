from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.core.config import get_settings

settings = get_settings()

# Hash used when the email doesn't exist, so login takes the same time either way.
_DUMMY_HASH = bcrypt.hashpw(b"dummy-password", bcrypt.gensalt()).decode()


def hash_password(password: str) -> str:
    # bcrypt generates a random salt and embeds it in the hash string.
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


def burn_password_check(password: str) -> None:
    """Spend the same CPU time as a real check (anti timing-attack)."""
    verify_password(password, _DUMMY_HASH)


def create_access_token(subject: str | int) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(subject),  # JWT spec: subject must be a string
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict:
    """Raises jwt.PyJWTError (expired, bad signature, malformed...) on failure."""
    return jwt.decode(
        token,
        settings.secret_key,
        algorithms=[settings.jwt_algorithm],  # always pass an allow-list
        options={"require": ["exp", "sub"]},
    )