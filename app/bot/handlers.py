from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards import (
    main_menu_keyboard,
    mini_app_keyboard,
    reset_confirm_keyboard,
)
from app.bot.renderer import send_app_launcher, send_start_card
from app.content.models import UiTexts
from app.content.registry import ScenarioRegistry
from app.db.repositories import ProgressRepository, UserRepository
from app.services.progress import ProgressService

router = Router()


def _progress_service(
    db_session: AsyncSession,
    scenario_registry: ScenarioRegistry,
    privacy_version: str,
) -> ProgressService:
    return ProgressService(
        user_repository=UserRepository(db_session),
        progress_repository=ProgressRepository(db_session),
        registry=scenario_registry,
        privacy_version=privacy_version,
    )


@router.message(Command("start"))
async def start_handler(
    message: Message,
    db_session: AsyncSession,
    ui_texts: UiTexts,
    scenario_registry: ScenarioRegistry,
    privacy_version: str,
    mini_app_url: str,
) -> None:
    service = _progress_service(db_session, scenario_registry, privacy_version)
    user = await service.get_or_create_user(message.from_user.id if message.from_user else 0)
    progress = await service.get_current_progress(user.telegram_user_id)
    await send_start_card(
        message=message,
        reply_markup=main_menu_keyboard(
            ui_texts,
            has_age=user.age_group is not None,
            mini_app_url=mini_app_url,
            continue_route=bool(progress and progress.trainer_session.status == "active"),
        ),
    )


@router.message(Command("app"))
async def app_handler(message: Message, mini_app_url: str) -> None:
    await send_app_launcher(
        message,
        mini_app_keyboard(mini_app_url),
    )


@router.message(Command("about"))
async def about_handler(message: Message, ui_texts: UiTexts) -> None:
    await message.answer(ui_texts.about_text)


@router.message(Command("help"))
async def help_handler(message: Message, ui_texts: UiTexts) -> None:
    await message.answer(ui_texts.help_text)


@router.message(Command("privacy"))
async def privacy_handler(message: Message, ui_texts: UiTexts) -> None:
    await message.answer(ui_texts.privacy_text)


@router.message(Command("reset"))
async def reset_handler(message: Message, ui_texts: UiTexts) -> None:
    await message.answer(ui_texts.reset_prompt, reply_markup=reset_confirm_keyboard(ui_texts))


@router.callback_query(F.data.startswith("reset:"))
async def reset_callback_handler(
    callback: CallbackQuery,
    db_session: AsyncSession,
    ui_texts: UiTexts,
    scenario_registry: ScenarioRegistry,
    privacy_version: str,
) -> None:
    service = _progress_service(db_session, scenario_registry, privacy_version)
    if callback.data == "reset:yes" and callback.from_user:
        await service.reset_user_progress(callback.from_user.id)
        await callback.message.answer(ui_texts.reset_done) if callback.message else None
    else:
        await callback.message.answer(ui_texts.menu_text) if callback.message else None
    await callback.answer()


@router.callback_query(F.data.startswith("a:"))
async def age_handler(
    callback: CallbackQuery,
    mini_app_url: str,
) -> None:
    if isinstance(callback.message, Message):
        await send_app_launcher(
            callback.message,
            mini_app_keyboard(mini_app_url),
        )
    await callback.answer()


@router.callback_query(F.data.startswith("m:"))
async def menu_handler(
    callback: CallbackQuery,
    ui_texts: UiTexts,
    mini_app_url: str,
) -> None:
    message = callback.message
    if not isinstance(message, Message):
        await callback.answer()
        return
    # Buttons from older bot messages can still be tapped. Route every legacy
    # menu action safely to the single Mini App entry point.
    await send_app_launcher(
        message,
        main_menu_keyboard(ui_texts, has_age=False, mini_app_url=mini_app_url),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("s:"))
async def scenario_callback_handler(
    callback: CallbackQuery,
    mini_app_url: str,
) -> None:
    if isinstance(callback.message, Message):
        await send_app_launcher(
            callback.message,
            mini_app_keyboard(mini_app_url),
        )
    await callback.answer()


@router.message()
async def fallback_message_handler(
    message: Message,
    ui_texts: UiTexts,
    mini_app_url: str,
) -> None:
    await send_app_launcher(
        message,
        main_menu_keyboard(ui_texts, False, mini_app_url),
    )
