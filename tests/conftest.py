# ruff: noqa: E402
# Env vars MUST be set before importing the app, because the app reads settings
# and creates its engine at import time. Forcing them here guarantees the test
# run can never touch your real database or real secret.
import os

os.environ["DATABASE_URL"] = "sqlite://"  # in-memory
os.environ["SECRET_KEY"] = "test-secret-key-not-for-production-0123456789"
os.environ["DEBUG"] = "false"

from collections.abc import Callable, Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app import models  # noqa: F401  (registers tables on Base.metadata)
from app.db.session import Base, get_db
from app.main import app

DEFAULT_PASSWORD = "StrongPass123"


@pytest.fixture()
def engine() -> Generator[Engine, None, None]:
    """A fresh empty in-memory SQLite database for EVERY test (full isolation)."""
    eng = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,  # one shared connection, so the in-memory DB persists
    )
    Base.metadata.create_all(eng)
    yield eng
    Base.metadata.drop_all(eng)
    eng.dispose()


@pytest.fixture()
def db_session(engine: Engine) -> Generator[Session, None, None]:
    """Direct DB access for tests that need to set up state (e.g. deactivate a user)."""
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with factory() as session:
        yield session


@pytest.fixture()
def client(engine: Engine) -> Generator[TestClient, None, None]:
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def override_get_db() -> Generator[Session, None, None]:
        db = factory()
        try:
            yield db
        finally:
            db.close()

    # Swap the real DB dependency for the test one.
    app.dependency_overrides[get_db] = override_get_db
    # Not used as a context manager on purpose: that would run the app's lifespan
    # (create_all on the real engine). Our fixtures create the tables instead.
    yield TestClient(app)
    app.dependency_overrides.clear()


def register_and_login(
    client: TestClient, email: str, password: str = DEFAULT_PASSWORD
) -> dict[str, str]:
    """Register a user, log in, and return ready-to-use auth headers."""
    r = client.post("/auth/register", json={"email": email, "password": password})
    assert r.status_code == 201, r.text
    r = client.post("/auth/login", data={"username": email, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture()
def auth_headers(client: TestClient) -> dict[str, str]:
    return register_and_login(client, "alice@example.com")


@pytest.fixture()
def other_auth_headers(client: TestClient) -> dict[str, str]:
    return register_and_login(client, "bob@example.com")


@pytest.fixture()
def make_task(client: TestClient) -> Callable[..., dict]:
    """Factory fixture: make_task(headers, title=..., priority=...) -> task JSON."""

    def _make(headers: dict[str, str], **fields) -> dict:
        payload = {"title": "Write tests", **fields}
        r = client.post("/tasks", json=payload, headers=headers)
        assert r.status_code == 201, r.text
        return r.json()

    return _make