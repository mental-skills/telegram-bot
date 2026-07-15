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

    @property
    def scenario_path(self) -> Path:
        return self.content_dir / f"{self.scenario_id}.json"

    @property
    def schema_path(self) -> Path:
        return self.content_dir / "scenario.schema.json"

    @property
    def ui_texts_path(self) -> Path:
        return self.content_dir / "ui_texts.ru.json"

    @property
    def asset_manifest_path(self) -> Path:
        return self.assets_dir / "asset_manifest.json"

    @property
    def visual_usage_map_path(self) -> Path:
        return self.assets_dir / "visual_usage_map.json"

    @property
    def brand_tokens_path(self) -> Path:
        return self.assets_dir / "brand_tokens.json"


@lru_cache
def get_settings() -> Settings:
    return Settings()
