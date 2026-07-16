from app.bot.keyboards import main_menu_keyboard
from app.content.repository import ContentRepository


def test_main_menu_contains_telegram_web_app_button(
    content_repository: ContentRepository,
) -> None:
    url = "https://mini-app.example.com"
    ui_texts = content_repository.get_ui_texts()

    keyboard = main_menu_keyboard(ui_texts, has_age=True, mini_app_url=url)

    button = keyboard.inline_keyboard[0][0]
    assert button.text == "Открыть Mini App"
    assert button.web_app is not None
    assert button.web_app.url == url
