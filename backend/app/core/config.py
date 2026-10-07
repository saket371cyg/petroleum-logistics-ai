"""Centralized application configuration.

The project intentionally keeps runtime configuration in environment variables so
it can run locally with SQLite and still work with Postgres in Docker.
"""

from __future__ import annotations

import logging
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger("petro_dealer.config")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    DATABASE_URL: str = "sqlite:///./data/petro_dealer.db"

    JWT_SECRET_KEY: str = "dev_secret_key_do_not_use_in_prod"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"
    MAX_REQUEST_SIZE_BYTES: int = 10_000_000
    LOGIN_RATE_LIMIT: int = 5
    LOGIN_RATE_WINDOW_SECONDS: int = 60

    DEFAULT_COVERAGE_DAYS: float = 5.0
    DEFAULT_SAFETY_STOCK_DAYS: float = 2.0
    STOCK_WARNING_DAYS: float = 3.0
    STOCK_CRITICAL_DAYS: float = 1.5

    ANTHROPIC_API_KEY: str | None = None
    ANTHROPIC_MODEL: str = "claude-sonnet-5-5"

    @field_validator("JWT_SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, value: str) -> str:
        placeholders = {
            "dev_secret_key_do_not_use_in_prod",
            "change_this_secret_in_production",
            "jwt_secret_key",
            "secret",
        }
        if value in placeholders:
            logger.warning(
                "JWT_SECRET_KEY is using a placeholder value. Set a strong secret in the environment before production use."
            )
        return value

    @property
    def cors_origins(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


settings = Settings()
