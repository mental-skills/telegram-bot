from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    telegram_bot_token: str = Field(default="", alias="TELEGRAM_BOT_TOKEN")
    database_url: str = Field(
        default="postgresql+asyncpg://mental:mental@db:5432/mental_skills",
        alias="DATABASE_URL",
    )
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    content_dir: Path = Field(default=Path("content"), alias="CONTENT_DIR")
    assets_dir: Path = Field(default=Path("assets"), alias="ASSETS_DIR")
    scenario_id: str = Field(default="PREMATCH_INSTRUCTIONS_02", alias="SCENARIO_ID")
    privacy_version: str = Field(default="2026-07-15", alias="PRIVACY_VERSION")
    rate_limit_messages_per_minute: int = Field(default=30, alias="RATE_LIMIT_MESSAGES_PER_MINUTE")
    environment: str = Field(default="development", alias="ENVIRONMENT")
    mini_app_url: str = Field(default="http://localhost:8080", alias="MINI_APP_URL")
    telegram_bot_username: str = Field(default="", alias="TELEGRAM_BOT_USERNAME")
    telegram_auth_max_age_seconds: int = Field(
        default=3600, alias="TELEGRAM_AUTH_MAX_AGE_SECONDS"
    )
    webapp_session_secret: str = Field(
        default="local-development-session-secret-change-me",
        alias="WEBAPP_SESSION_SECRET",
    )
    webapp_session_ttl_seconds: int = Field(
        default=3600, alias="WEBAPP_SESSION_TTL_SECONDS"
    )
    session_cookie_secure: bool = Field(default=False, alias="SESSION_COOKIE_SECURE")
    dev_auth_enabled: bool = Field(default=False, alias="DEV_AUTH_ENABLED")
    dev_auth_telegram_user_id: int = Field(default=900000001, alias="DEV_AUTH_TELEGRAM_USER_ID")

    @property
    def scenario_path(self) -> Path:
        return self.content_dir / f"{self.scenario_id}.json"

    @property
    def scenario_catalog_path(self) -> Path:
        return self.content_dir / "scenario_catalog.json"

    @property
    def schema_path(self) -> Path:
        return self.content_dir / "scenario.schema.json"

    @property
    def ui_texts_path(self) -> Path:
        return self.content_dir / "ui_texts.ru.json"

    @property
    def mini_app_visuals_path(self) -> Path:
        return self.content_dir / "mini_app_visuals.json"

    @property
    def asset_manifest_path(self) -> Path:
        return self.assets_dir / "asset_manifest.json"

    @property
    def visual_usage_map_path(self) -> Path:
        return self.assets_dir / "visual_usage_map.json"

    @property
    def brand_tokens_path(self) -> Path:
        return self.assets_dir / "brand_tokens.json"

    @property
    def mini_app_asset_manifest_path(self) -> Path:
        return self.assets_dir / "mini_app" / "manifest.json"


@lru_cache
def get_settings() -> Settings:
    return Settings()
