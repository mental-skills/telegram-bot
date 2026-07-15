from __future__ import annotations

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from app.assets.repository import AssetRepository
from app.bot.handlers import router
from app.bot.middleware import DbSessionMiddleware
from app.content.registry import ScenarioRegistry
from app.content.repository import ContentRepository
from app.core.config import Settings
from app.db.session import create_sessionmaker
from app.services.rate_limit import InMemoryRateLimitMiddleware


def build_dispatcher(settings: Settings) -> Dispatcher:
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

    sessionmaker = create_sessionmaker(settings)
    dispatcher = Dispatcher(
        asset_repository=asset_repository,
        ui_texts=ui_texts,
        scenario_registry=registry,
        privacy_version=settings.privacy_version,
    )
    dispatcher.update.middleware(DbSessionMiddleware(sessionmaker))
    dispatcher.update.middleware(
        InMemoryRateLimitMiddleware(settings.rate_limit_messages_per_minute)
    )
    dispatcher.include_router(router)
    return dispatcher


def build_bot(settings: Settings) -> Bot:
    if not settings.telegram_bot_token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is required")
    return Bot(
        token=settings.telegram_bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
