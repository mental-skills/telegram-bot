from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

from app.bot.callbacks import age_callback, menu_callback, reset_callback
from app.content.models import AgeGroup, UiTexts
from app.engine.types import ScenarioScreen
from app.services.progress import CallbackPayload


def main_menu_keyboard(
    ui: UiTexts,
    has_age: bool,
    mini_app_url: str | None = None,
) -> InlineKeyboardMarkup:
    buttons: list[list[InlineKeyboardButton]] = []
    if mini_app_url:
        buttons.append(
            [
                InlineKeyboardButton(
                    text="Открыть Mini App",
                    web_app=WebAppInfo(url=mini_app_url),
                )
            ]
        )
    buttons.extend([
        [InlineKeyboardButton(text=ui.continue_training, callback_data=menu_callback("continue"))],
        [
            InlineKeyboardButton(
                text=ui.start_scenario_02,
                callback_data=menu_callback("scenario_02"),
            )
        ],
        [InlineKeyboardButton(text=ui.tools, callback_data=menu_callback("tools"))],
        [InlineKeyboardButton(text=ui.about, callback_data=menu_callback("about"))],
        [InlineKeyboardButton(text=ui.privacy, callback_data=menu_callback("privacy"))],
    ])
    if has_age:
        buttons.append(
            [InlineKeyboardButton(text=ui.change_age, callback_data=menu_callback("age"))]
        )
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def age_keyboard(ui: UiTexts) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=ui.age_6_8, callback_data=age_callback("6-8"))],
            [InlineKeyboardButton(text=ui.age_9_12, callback_data=age_callback("9-12"))],
            [InlineKeyboardButton(text=ui.age_13_16, callback_data=age_callback("13-16"))],
            [InlineKeyboardButton(text=ui.back_to_menu, callback_data=menu_callback("home"))],
        ]
    )


def scenario_keyboard(
    screen: ScenarioScreen,
    session_id: int,
    revision: int,
) -> InlineKeyboardMarkup | None:
    if not screen.buttons:
        return None
    rows: list[list[InlineKeyboardButton]] = []
    for button in screen.buttons:
        payload = CallbackPayload(
            session_id=session_id,
            revision=revision,
            option_id=button.id,
        ).pack()
        rows.append([InlineKeyboardButton(text=button.label, callback_data=payload)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def restart_keyboard(ui: UiTexts) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=ui.restart, callback_data=menu_callback("restart"))],
            [InlineKeyboardButton(text=ui.back_to_menu, callback_data=menu_callback("home"))],
        ]
    )


def reset_confirm_keyboard(ui: UiTexts) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=ui.confirm_reset, callback_data=reset_callback(True))],
            [InlineKeyboardButton(text=ui.cancel, callback_data=reset_callback(False))],
        ]
    )


def age_from_callback(raw: str) -> AgeGroup | None:
    if raw in {"a:6-8", "a:9-12", "a:13-16"}:
        return raw.removeprefix("a:")  # type: ignore[return-value]
    return None
