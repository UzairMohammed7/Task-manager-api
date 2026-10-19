from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text

from app import models  # noqa: F401  (registers tables on Base.metadata)
from app.core.config import get_settings
from app.db.session import Base, engine
from app.deps import DbSession

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    # Create tables that don't exist yet. create_all never alters existing
    # tables. That is the gap Alembic fills (see note below).
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug,
    lifespan=lifespan,
)


@app.get("/", tags=["health"])
def hello() -> dict[str, str]:
    return {"message": "Hello from the Task Manager API"}


@app.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    return {"status": "ok", "version": settings.app_version}


@app.get("/health/db", tags=["health"])
def db_health_check(db: DbSession) -> dict[str, str]:
    """Proves dependency injection + DB connectivity work end to end."""
    db.execute(text("SELECT 1"))
    return {"database": "ok"}