from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings, loaded from environment variables / .env file."""

    app_name: str = "Task Manager API"
    app_version: str = "0.1.0"
    debug: bool = False
    database_url: str = "sqlite:///./task_manager.db"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    secret_key: str                       # no default on purpose: app refuses to start without it
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30


@lru_cache
def get_settings() -> Settings:
    # Cached so the .env file is parsed once, not on every request.
    return Settings()