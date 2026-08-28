"""Configuration for both services.

Secrets come from the process environment first, then from ./.env.spenden at the repository root.
There is deliberately no second env file: this project is not an AthenaRun product and must never
inherit credentials from a neighbouring repository. A test asserts that.

With ENV=production the application refuses to start unless ADMIN_TOKEN and DATABASE_URL are set,
because a read-only public API with an open ingestion trigger is not a read-only public API.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[3]
ENV_FILE = REPO_ROOT / ".env.spenden"

ASYNC_DRIVER = "postgresql+asyncpg://"
SYNC_DRIVER = "postgresql+psycopg://"
MIN_ADMIN_TOKEN_BYTES = 32


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    env: Literal["development", "test", "production"] = "development"
    log_level: str = "INFO"

    database_url: str | None = None
    database_url_sync: str | None = None

    admin_token: SecretStr | None = None
    anthropic_api_key: SecretStr | None = None

    # Exact origins only. The API is public and read-only, but "*" would also allow a page that
    # impersonates this one to read it as if it were first-party.
    cors_origins: list[str] = []

    # Ingestion gates. Defaults are the spec's numbers.
    max_reports_per_run: int = 25
    max_run_cost_usd: float = 1.0
    reliefweb_min_interval_s: float = 2.0

    user_agent: str = "spenden-transparenz/0.1 (+https://github.com/ChristianMLux/spenden-transparenz)"
    allowed_fetch_hosts: tuple[str, ...] = ("reliefweb.int", "api.reliefweb.int")

    @field_validator("cors_origins")
    @classmethod
    def _no_wildcard_origin(cls, value: list[str]) -> list[str]:
        if "*" in value:
            raise ValueError("cors_origins must list exact origins, never the wildcard '*'")
        return value

    @model_validator(mode="after")
    def _production_requires_its_secrets(self) -> Settings:
        if self.env != "production":
            return self
        if self.database_url is None:
            raise ValueError("DATABASE_URL is required when ENV=production")
        if self.admin_token is None:
            raise ValueError("ADMIN_TOKEN is required when ENV=production")
        if len(self.admin_token.get_secret_value().encode()) < MIN_ADMIN_TOKEN_BYTES:
            raise ValueError(f"ADMIN_TOKEN must be at least {MIN_ADMIN_TOKEN_BYTES} bytes when ENV=production")
        return self

    @property
    def async_url(self) -> str:
        """URL for the application. Raises rather than falling back, so a missing database is loud."""
        if self.database_url is None:
            raise RuntimeError("DATABASE_URL is not configured")
        return _with_driver(self.database_url, ASYNC_DRIVER)

    @property
    def sync_url(self) -> str:
        """URL for Alembic. Explicit DATABASE_URL_SYNC wins; otherwise derived from DATABASE_URL."""
        if self.database_url_sync:
            return self.database_url_sync
        if self.database_url is None:
            raise RuntimeError("DATABASE_URL is not configured")
        return _with_driver(self.database_url, SYNC_DRIVER)


def _with_driver(url: str, driver: str) -> str:
    _, _, rest = url.partition("://")
    return driver + rest


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
