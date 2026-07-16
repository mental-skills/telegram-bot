from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from app.bot.keyboards import main_menu_keyboard, mini_app_keyboard
from app.bot.renderer import BOT_WELCOME_TEXT, send_start_card
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


class _Bot:
    def __init__(self, *, fail_photo: bool = False) -> None:
        self.fail_photo = fail_photo
        self.photos: list[dict[str, Any]] = []

    async def send_photo(self, **kwargs: Any) -> None:
        if self.fail_photo:
            raise RuntimeError("photo unavailable")
        self.photos.append(kwargs)


class _Chat:
    id = 123


class _Message:
    def __init__(self, bot: _Bot) -> None:
        self.bot = bot
        self.chat = _Chat()
        self.answers: list[tuple[str, Any]] = []

    async def answer(self, text: str, *, reply_markup: Any = None) -> None:
        self.answers.append((text, reply_markup))


@pytest.mark.asyncio
async def test_start_sends_one_photo_with_caption_and_web_app(
    asset_repository: Any,
) -> None:
    bot = _Bot()
    message = _Message(bot)
    keyboard = mini_app_keyboard("https://mini-app.example.com")

    await send_start_card(message, asset_repository, keyboard)  # type: ignore[arg-type]

    assert len(bot.photos) == 1
    assert not message.answers
    sent = bot.photos[0]
    assert sent["caption"] == BOT_WELCOME_TEXT
    assert "Семь ситуаций до, во время и после матча." in sent["caption"]
    assert "не ставит диагнозы" in sent["caption"]
    assert sent["reply_markup"] == keyboard
    assert Path(sent["photo"].path).name == "brand_logo_telegram_welcome.png"


@pytest.mark.asyncio
async def test_start_photo_failure_uses_same_text_and_button_fallback(
    asset_repository: Any,
) -> None:
    bot = _Bot(fail_photo=True)
    message = _Message(bot)
    keyboard = mini_app_keyboard("https://mini-app.example.com")

    await send_start_card(message, asset_repository, keyboard)  # type: ignore[arg-type]

    assert not bot.photos
    assert message.answers == [(BOT_WELCOME_TEXT, keyboard)]


def test_welcome_asset_is_runtime_and_allowed_for_bot_start(asset_repository: Any) -> None:
    asset = asset_repository.get_runtime_asset("brand_logo_telegram_welcome")
    assert asset.runtime is True
    assert "bot_start" in asset.allowed_roles
    assert "about_project" in asset.allowed_roles
    assert asset.path.name == "brand_logo_telegram_welcome.png"
