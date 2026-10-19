from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings

settings = get_settings()

# SQLite forbids sharing a connection across threads by default, and FastAPI
# runs sync routes in a threadpool, so we relax that check for SQLite only.
connect_args = (
    {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
)

engine = create_engine(
    settings.database_url,
    connect_args=connect_args,
    pool_pre_ping=True,  # drop dead connections (useful with Postgres)
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,  # objects stay readable after commit()
)


class Base(DeclarativeBase):
    """Parent class for all ORM models; Base.metadata knows every table."""


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency: one session per request, always closed afterwards."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()