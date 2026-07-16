from __future__ import annotations

import logging

from aiogram import Bot
from aiogram.types import CallbackQuery, FSInputFile, InlineKeyboardMarkup, Message

from app.assets.repository import AssetRepository
from app.bot.keyboards import scenario_keyboard
from app.content.models import UiTexts
from app.db.models import TrainerSession
from app.engine.types import ScenarioScreen

logger = logging.getLogger(__name__)

TELEGRAM_CAPTION_LIMIT = 1024


def format_screen_text(screen: ScenarioScreen) -> str:
    parts: list[str] = []
    if screen.title:
        parts.append(f"<b>{screen.title}</b>")
    if screen.text:
        parts.append(screen.text)
    if screen.quote:
        parts.append(f"<b>Готовая фраза:</b>\n{screen.quote}")
    return "\n\n".join(parts)


async def send_start_card(
    message: Message,
    asset_repository: AssetRepository,
    ui: UiTexts,
    reply_markup: InlineKeyboardMarkup,
) -> None:
    text = f"<b>{ui.start_title}</b>\n\n{ui.start_text}"
    if message.bot is None:
        return
    await _send_optional_photo(
        bot=message.bot,
        chat_id=message.chat.id,
        asset_repository=asset_repository,
        asset_id="brand_logo_horizontal",
        text=text,
        reply_markup=reply_markup,
    )


async def send_screen(
    target: Message | CallbackQuery,
    asset_repository: AssetRepository,
    screen: ScenarioScreen,
    trainer_session: TrainerSession,
) -> None:
    message = target.message if isinstance(target, CallbackQuery) else target
    if message is None:
        return
    if message.bot is None:
        return
    text = format_screen_text(screen)
    reply_markup = scenario_keyboard(
        screen=screen,
        session_id=trainer_session.id,
        revision=trainer_session.current_revision,
    )
    if screen.media is None:
        await message.answer(text, reply_markup=reply_markup)
        return
    await _send_optional_photo(
        bot=message.bot,
        chat_id=message.chat.id,
        asset_repository=asset_repository,
        asset_id=screen.media.asset_id,
        text=text,
        reply_markup=reply_markup,
    )


async def _send_optional_photo(
    bot: Bot,
    chat_id: int,
    asset_repository: AssetRepository,
    asset_id: str,
    text: str,
    reply_markup: InlineKeyboardMarkup | None,
) -> None:
    try:
        asset = asset_repository.get_runtime_asset(asset_id)
        photo = FSInputFile(asset.path)
        if len(text) <= TELEGRAM_CAPTION_LIMIT:
            await bot.send_photo(
                chat_id=chat_id, photo=photo, caption=text, reply_markup=reply_markup
            )
        else:
            await bot.send_photo(chat_id=chat_id, photo=photo)
            await bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup)
    except Exception as exc:
        logger.warning("media_fallback asset_id=%s error=%s", asset_id, exc.__class__.__name__)
        await bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup)
