from __future__ import annotations

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from app.application import build_runtime
from app.bot.handlers import router
from app.bot.middleware import DbSessionMiddleware
from app.core.config import Settings
from app.services.rate_limit import InMemoryRateLimitMiddleware


def build_dispatcher(settings: Settings) -> Dispatcher:
    runtime = build_runtime(settings)
    dispatcher = Dispatcher(
        asset_repository=runtime.asset_repository,
        ui_texts=runtime.ui_texts,
        scenario_registry=runtime.scenario_registry,
        privacy_version=settings.privacy_version,
        mini_app_url=settings.mini_app_url,
    )
    dispatcher.update.middleware(DbSessionMiddleware(runtime.sessionmaker))
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
