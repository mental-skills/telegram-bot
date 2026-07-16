from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.assets.repository import AssetRepository
from app.bot.keyboards import (
    age_from_callback,
    age_keyboard,
    main_menu_keyboard,
    reset_confirm_keyboard,
)
from app.bot.renderer import send_screen, send_start_card
from app.content.models import UiTexts
from app.content.registry import ScenarioRegistry
from app.db.repositories import ProgressRepository, UserRepository
from app.services.progress import STANDALONE_MODULE_ID, ProgressService

STANDALONE_SCENARIO_02 = "PREMATCH_INSTRUCTIONS_02"

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
    asset_repository: AssetRepository,
    ui_texts: UiTexts,
    scenario_registry: ScenarioRegistry,
    privacy_version: str,
    mini_app_url: str,
) -> None:
    service = _progress_service(db_session, scenario_registry, privacy_version)
    user = await service.get_or_create_user(message.from_user.id if message.from_user else 0)
    await send_start_card(
        message=message,
        asset_repository=asset_repository,
        ui=ui_texts,
        reply_markup=main_menu_keyboard(
            ui_texts,
            has_age=user.age_group is not None,
            mini_app_url=mini_app_url,
        ),
    )


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
    db_session: AsyncSession,
    ui_texts: UiTexts,
    scenario_registry: ScenarioRegistry,
    privacy_version: str,
    mini_app_url: str,
) -> None:
    age_group = age_from_callback(callback.data or "")
    if age_group is None or callback.from_user is None:
        await callback.answer(ui_texts.generic_error, show_alert=True)
        return
    service = _progress_service(db_session, scenario_registry, privacy_version)
    await service.set_age(callback.from_user.id, age_group)
    if isinstance(callback.message, Message):
        await callback.message.answer(
            ui_texts.age_saved,
            reply_markup=main_menu_keyboard(ui_texts, True, mini_app_url),
        )
    await callback.answer()


@router.callback_query(F.data.startswith("m:"))
async def menu_handler(
    callback: CallbackQuery,
    db_session: AsyncSession,
    asset_repository: AssetRepository,
    ui_texts: UiTexts,
    scenario_registry: ScenarioRegistry,
    privacy_version: str,
    mini_app_url: str,
) -> None:
    service = _progress_service(db_session, scenario_registry, privacy_version)
    user = await service.get_or_create_user(callback.from_user.id)
    action = (callback.data or "").removeprefix("m:")
    message = callback.message
    if not isinstance(message, Message):
        await callback.answer()
        return
    if action == "age":
        await message.answer(ui_texts.age_prompt, reply_markup=age_keyboard(ui_texts))
    elif action == "continue":
        progress = await service.start_or_continue(callback.from_user.id)
        if progress is None:
            await message.answer(ui_texts.age_prompt, reply_markup=age_keyboard(ui_texts))
        else:
            await send_screen(callback, asset_repository, progress.screen, progress.trainer_session)
    elif action == "restart":
        progress = await service.restart(callback.from_user.id)
        if progress is None:
            await message.answer(ui_texts.age_prompt, reply_markup=age_keyboard(ui_texts))
        else:
            await send_screen(callback, asset_repository, progress.screen, progress.trainer_session)
    elif action == "scenario_02":
        progress = await service.start_or_continue_standalone(
            callback.from_user.id,
            STANDALONE_SCENARIO_02,
        )
        if progress is None:
            await message.answer(ui_texts.age_prompt, reply_markup=age_keyboard(ui_texts))
        else:
            await send_screen(callback, asset_repository, progress.screen, progress.trainer_session)
    elif action == "scenario_02_restart":
        progress = await service.restart_scenario(
            callback.from_user.id,
            STANDALONE_SCENARIO_02,
            STANDALONE_MODULE_ID,
        )
        if progress is None:
            await message.answer(ui_texts.age_prompt, reply_markup=age_keyboard(ui_texts))
        else:
            await send_screen(callback, asset_repository, progress.screen, progress.trainer_session)
    elif action == "tools":
        await message.answer(ui_texts.tools_text)
    elif action == "about":
        await message.answer(ui_texts.about_text)
    elif action == "privacy":
        await message.answer(ui_texts.privacy_text)
    else:
        await message.answer(
            ui_texts.menu_text,
            reply_markup=main_menu_keyboard(
                ui_texts,
                user.age_group is not None,
                mini_app_url,
            ),
        )
    await callback.answer()


@router.callback_query(F.data.startswith("s:"))
async def scenario_callback_handler(
    callback: CallbackQuery,
    db_session: AsyncSession,
    asset_repository: AssetRepository,
    ui_texts: UiTexts,
    scenario_registry: ScenarioRegistry,
    privacy_version: str,
    mini_app_url: str,
) -> None:
    if callback.from_user is None:
        await callback.answer(ui_texts.generic_error, show_alert=True)
        return
    service = _progress_service(db_session, scenario_registry, privacy_version)
    try:
        result = await service.handle_callback(callback.from_user.id, callback.data or "")
    except Exception:
        await callback.answer(ui_texts.generic_error, show_alert=True)
        return

    if result.status == "ok" and result.progress_screen:
        await send_screen(
            callback,
            asset_repository,
            result.progress_screen.screen,
            result.progress_screen.trainer_session,
        )
    elif result.status == "main_menu" and callback.message:
        user = await service.get_or_create_user(callback.from_user.id)
        await callback.message.answer(
            ui_texts.menu_text,
            reply_markup=main_menu_keyboard(
                ui_texts,
                user.age_group is not None,
                mini_app_url,
            ),
        )
    elif result.status == "next_unavailable" and callback.message:
        await callback.message.answer(
            ui_texts.scenario_unavailable,
            reply_markup=main_menu_keyboard(ui_texts, True, mini_app_url),
        )
    elif result.status == "duplicate":
        await callback.answer(ui_texts.duplicate_callback, show_alert=True)
        return
    else:
        await callback.answer(ui_texts.stale_callback, show_alert=True)
        return
    await callback.answer()


@router.message()
async def fallback_message_handler(
    message: Message,
    ui_texts: UiTexts,
    mini_app_url: str,
) -> None:
    await message.answer(
        ui_texts.menu_text,
        reply_markup=main_menu_keyboard(ui_texts, False, mini_app_url),
    )
