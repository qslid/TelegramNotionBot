"""Pydantic Settings loaded from environment / .env."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve .env relative to repo root (two levels above this file: bot/config → repo)
_REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Runtime configuration. Secrets must come from env — never commit .env."""

    model_config = SettingsConfigDict(
        env_file=str(_REPO_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    bot_token: str = Field(..., alias="BOT_TOKEN", description="Telegram Bot API token")

    database_url: str = Field(
        default="sqlite+aiosqlite:///./bot.db",
        alias="DATABASE_URL",
        description="SQLAlchemy async URL (SQLite default, PostgreSQL optional)",
    )

    daily_request_limit: int = Field(default=100, alias="DAILY_REQUEST_LIMIT", ge=1)
    monthly_request_limit: int = Field(default=2000, alias="MONTHLY_REQUEST_LIMIT", ge=1)
    throttle_rate_seconds: float = Field(default=2.0, alias="THROTTLE_RATE_SECONDS", gt=0)
    max_file_size_bytes: int = Field(
        default=20 * 1024 * 1024,
        alias="MAX_FILE_SIZE_BYTES",
        ge=1,
    )
    default_locale: str = Field(default="en", alias="DEFAULT_LOCALE")


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton for the process lifetime."""
    return Settings()  # type: ignore[call-arg]
