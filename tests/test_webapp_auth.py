from __future__ import annotations

import hashlib
import hmac
import json
from urllib.parse import urlencode

import pytest

from app.api.auth import SessionTokenManager, TelegramInitDataValidator, WebAppAuthError
from app.api.main import create_api_app
from app.core.config import Settings

BOT_TOKEN = "123456:test-token"  # noqa: S105 - non-secret test fixture


def make_init_data(user_id: int, auth_date: int, token: str = BOT_TOKEN) -> str:
    data = {
        "auth_date": str(auth_date),
        "query_id": "test-query",
        "user": json.dumps({"id": user_id, "first_name": "Test"}, separators=(",", ":")),
    }
    check_string = "\n".join(f"{key}={data[key]}" for key in sorted(data))
    secret = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
    data["hash"] = hmac.new(secret, check_string.encode(), hashlib.sha256).hexdigest()
    return urlencode(data)


def test_valid_telegram_init_data() -> None:
    validator = TelegramInitDataValidator(BOT_TOKEN, max_age_seconds=3600)
    result = validator.validate(make_init_data(12345, 1_000), now=1_100)
    assert result.telegram_user_id == 12345
    assert result.auth_date == 1_000


def test_invalid_telegram_init_data_signature() -> None:
    validator = TelegramInitDataValidator(BOT_TOKEN, max_age_seconds=3600)
    raw = make_init_data(12345, 1_000).replace("12345", "99999")
    with pytest.raises(WebAppAuthError, match="signature"):
        validator.validate(raw, now=1_100)


def test_expired_telegram_init_data() -> None:
    validator = TelegramInitDataValidator(BOT_TOKEN, max_age_seconds=60)
    with pytest.raises(WebAppAuthError, match="expired"):
        validator.validate(make_init_data(12345, 1_000), now=1_061)


def test_signed_session_token() -> None:
    manager = SessionTokenManager("a" * 32, ttl_seconds=300)
    token = manager.issue(telegram_user_id=12345, now=1_000)
    assert manager.verify(token, now=1_200) == 12345
    with pytest.raises(WebAppAuthError, match="expired"):
        manager.verify(token, now=1_301)


def test_dev_auth_is_rejected_in_production() -> None:
    settings = Settings(
        ENVIRONMENT="production",
        DEV_AUTH_ENABLED=True,
        SESSION_COOKIE_SECURE=True,
        WEBAPP_SESSION_SECRET="a" * 32,
    )
    with pytest.raises(RuntimeError, match="DEV_AUTH_ENABLED"):
        create_api_app(settings=settings)
