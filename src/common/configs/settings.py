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

    model_config = SettingsConfigDict(env_file=".env", extra="allow")


@lru_cache()
def get_settings() -> Settings:
    """Get application settings."""
    return Settings()
