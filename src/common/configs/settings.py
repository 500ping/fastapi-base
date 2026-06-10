from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    debug: bool = True

    # CORS
    cors_allow_origins: List[str] = ["*"]
    cors_allow_credentials: bool = True
    cors_allow_methods: List[str] = ["*"]
    cors_allow_headers: List[str] = ["*"]

    # Database
    database_url: str = (
        "postgresql+psycopg://postgres:postgres@localhost:5432/fastapi_base"
    )
    db_connect_max_retries: int = 5
    db_connect_retry_delay: float = 2.0

    # Redis (used for distributed locks)
    redis_url: str = "redis://localhost:6379/0"
    redis_connect_max_retries: int = 5
    redis_connect_retry_delay: float = 2.0
    redis_lock_timeout: float = 10.0
    redis_lock_blocking_timeout: float = 10.0

    # JWT
    jwt_secret_key: str = "change-me-to-a-secure-random-secret-key"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    model_config = SettingsConfigDict(env_file=".env", extra="allow")


@lru_cache()
def get_settings() -> Settings:
    """Get application settings."""
    return Settings()
