"""Environment configuration with fail-closed deployed defaults."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Optional, Tuple


class SettingsError(ValueError):
    """Raised when runtime configuration violates a security boundary."""


@dataclass(frozen=True)
class Settings:
    app_env: str
    ai_provider: str
    database_path: Path
    auth_mode: str
    api_auth_token: Optional[str]
    allowed_origins: Tuple[str, ...]
    max_request_bytes: int = 128 * 1024

    def __post_init__(self) -> None:
        if self.app_env not in {"development", "test", "production"}:
            raise SettingsError("APP_ENV must be development, test, or production")
        if self.ai_provider not in {"mock", "gemini"}:
            raise SettingsError("AI_PROVIDER must be mock or gemini")
        if self.auth_mode not in {"dev", "token"}:
            raise SettingsError("AUTH_MODE must be dev or token")
        if self.app_env == "production" and self.auth_mode != "token":
            raise SettingsError("production requires token authentication")
        if self.auth_mode == "token" and not (
            self.api_auth_token and len(self.api_auth_token) >= 16
        ):
            raise SettingsError("token authentication requires a token of at least 16 characters")
        if not self.allowed_origins or "*" in self.allowed_origins:
            raise SettingsError("ALLOWED_ORIGINS must contain explicit origins")
        if not 1_024 <= self.max_request_bytes <= 1024 * 1024:
            raise SettingsError("request limit is outside the supported range")
        protected = {
            "20_areas",
            "25_self_management",
            "private",
            "credentials",
            ".env",
            ".obsidian",
        }
        if any(part.casefold() in protected for part in self.database_path.parts):
            raise SettingsError("DATABASE_URL cannot target a protected path")

    @classmethod
    def from_env(cls, environ: Optional[Mapping[str, str]] = None) -> "Settings":
        values = os.environ if environ is None else environ
        database_url = values.get(
            "DATABASE_URL", "sqlite:///./data/p1_5_capture.sqlite3"
        )
        prefix = "sqlite:///"
        if not database_url.startswith(prefix):
            raise SettingsError("P1.5 offline MVP supports only SQLite DATABASE_URL")
        database_value = database_url[len(prefix) :]
        if not database_value:
            raise SettingsError("DATABASE_URL requires a SQLite path")
        origins = tuple(
            origin.strip()
            for origin in values.get(
                "ALLOWED_ORIGINS", "http://127.0.0.1:8000"
            ).split(",")
            if origin.strip()
        )
        return cls(
            app_env=values.get("APP_ENV", "development"),
            ai_provider=values.get("AI_PROVIDER", "mock"),
            database_path=Path(database_value),
            auth_mode=values.get("AUTH_MODE", "dev"),
            api_auth_token=values.get("API_AUTH_TOKEN") or None,
            allowed_origins=origins,
        )
