from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.assets.repository import AssetRepository
from app.content.models import UiTexts
from app.content.registry import ScenarioRegistry
from app.content.repository import ContentRepository
from app.core.config import Settings
from app.db.session import create_sessionmaker
from app.mini_app.visuals import MiniAppVisualRepository


@dataclass(frozen=True)
class ApplicationRuntime:
    settings: Settings
    asset_repository: AssetRepository
    ui_texts: UiTexts
    scenario_registry: ScenarioRegistry
    mini_app_visuals: MiniAppVisualRepository
    sessionmaker: async_sessionmaker[AsyncSession]


def build_runtime(settings: Settings) -> ApplicationRuntime:
    if settings.environment == "production":
        if settings.dev_auth_enabled:
            raise RuntimeError("DEV_AUTH_ENABLED must be false in production")
        if not settings.mini_app_url.startswith("https://"):
            raise RuntimeError("MINI_APP_URL must use HTTPS in production")
    asset_repository = AssetRepository(
        manifest_path=settings.asset_manifest_path,
        visual_usage_map_path=settings.visual_usage_map_path,
        brand_tokens_path=settings.brand_tokens_path,
    )
    content_repository = ContentRepository(
        scenario_path=settings.scenario_path,
        schema_path=settings.schema_path,
        ui_texts_path=settings.ui_texts_path,
        asset_repository=asset_repository,
    )
    ui_texts = content_repository.get_ui_texts()
    registry = ScenarioRegistry.load(
        catalog_path=settings.scenario_catalog_path,
        schema_path=settings.schema_path,
        asset_repository=asset_repository,
        continue_label=ui_texts.continue_,
    )
    mini_app_visuals = MiniAppVisualRepository(
        manifest_path=settings.mini_app_asset_manifest_path,
        presentation_path=settings.mini_app_visuals_path,
    )
    mini_app_visuals.load()
    return ApplicationRuntime(
        settings=settings,
        asset_repository=asset_repository,
        ui_texts=ui_texts,
        scenario_registry=registry,
        mini_app_visuals=mini_app_visuals,
        sessionmaker=create_sessionmaker(settings),
    )
