from fastapi import FastAPI

from app.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug,
)


@app.get("/", tags=["health"])
def hello() -> dict[str, str]:
    return {"message": "Hello from the Task Manager API"}


@app.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    """Used later by Docker and CI to check the app is alive."""
    return {"status": "ok", "version": settings.app_version}