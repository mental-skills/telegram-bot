from __future__ import annotations

from typing import Any

import pytest
from aiogram.types import ReplyKeyboardRemove

from app.bot.keyboards import main_menu_keyboard, mini_app_keyboard
from app.bot.renderer import send_start_card
from app.content.repository import ContentRepository


def test_main_menu_is_single_mini_app_entry_point(
    content_repository: ContentRepository,
) -> None:
    url = "https://mini-app.example.com"
    ui_texts = content_repository.get_ui_texts()

    keyboard = main_menu_keyboard(ui_texts, has_age=True, mini_app_url=url)

    assert len(keyboard.inline_keyboard) == 1
    button = keyboard.inline_keyboard[0][0]
    assert button.text == "Открыть ментальный спортзал"
    assert button.callback_data is None
    assert button.web_app is not None
    assert button.web_app.url == url


def test_active_route_uses_only_continue_label() -> None:
    keyboard = mini_app_keyboard("https://mini-app.example.com", continue_route=True)

    assert len(keyboard.inline_keyboard) == 1
    assert keyboard.inline_keyboard[0][0].text == "Продолжить маршрут"


class _SentMessage:
    def __init__(self) -> None:
        self.edited_markup: Any = None

    async def edit_reply_markup(self, *, reply_markup: Any) -> None:
        self.edited_markup = reply_markup


class _Message:
    def __init__(self) -> None:
        self.answers: list[tuple[str, Any]] = []
        self.sent = _SentMessage()

    async def answer(self, text: str, *, reply_markup: Any = None) -> _SentMessage:
        self.answers.append((text, reply_markup))
        return self.sent


@pytest.mark.asyncio
async def test_start_removes_legacy_reply_keyboard_and_keeps_one_greeting() -> None:
    message = _Message()
    keyboard = mini_app_keyboard("https://mini-app.example.com")

    await send_start_card(message, keyboard)  # type: ignore[arg-type]

    assert len(message.answers) == 1
    assert message.answers[0][0].startswith("Mental Skills — ментальный спортзал")
    assert isinstance(message.answers[0][1], ReplyKeyboardRemove)
    assert message.sent.edited_markup == keyboard
