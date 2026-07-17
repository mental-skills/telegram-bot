from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import parse_qsl


class WebAppAuthError(ValueError):
    """Raised when Telegram authentication data cannot be trusted."""


@dataclass(frozen=True)
class ValidatedTelegramUser:
    telegram_user_id: int
    auth_date: int


class TelegramInitDataValidator:
    def __init__(self, bot_token: str, max_age_seconds: int) -> None:
        self.bot_token = bot_token
        self.max_age_seconds = max_age_seconds

    def validate(self, raw_init_data: str, now: int | None = None) -> ValidatedTelegramUser:
        if not self.bot_token:
            raise WebAppAuthError("Telegram bot token is not configured")
        try:
            pairs = parse_qsl(raw_init_data, keep_blank_values=True, strict_parsing=True)
        except ValueError as exc:
            raise WebAppAuthError("Invalid initData query string") from exc
        data: dict[str, str] = {}
        for key, value in pairs:
            if key in data:
                raise WebAppAuthError("Duplicate initData field")
            data[key] = value

        received_hash = data.pop("hash", "")
        if not received_hash:
            raise WebAppAuthError("initData hash is missing")
        data_check_string = "\n".join(f"{key}={data[key]}" for key in sorted(data))
        secret_key = hmac.new(
            b"WebAppData",
            self.bot_token.encode("utf-8"),
            hashlib.sha256,
        ).digest()
        expected_hash = hmac.new(
            secret_key,
            data_check_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(expected_hash, received_hash):
            raise WebAppAuthError("initData signature is invalid")

        try:
            auth_date = int(data["auth_date"])
        except (KeyError, ValueError) as exc:
            raise WebAppAuthError("initData auth_date is invalid") from exc
        current_time = int(time.time()) if now is None else now
        if auth_date > current_time + 30:
            raise WebAppAuthError("initData auth_date is in the future")
        if current_time - auth_date > self.max_age_seconds:
            raise WebAppAuthError("initData has expired")

        try:
            user_data = json.loads(data["user"])
            telegram_user_id = int(user_data["id"])
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise WebAppAuthError("initData user is invalid") from exc
        if telegram_user_id <= 0:
            raise WebAppAuthError("Telegram user id is invalid")
        return ValidatedTelegramUser(
            telegram_user_id=telegram_user_id,
            auth_date=auth_date,
        )


class SessionTokenManager:
    def __init__(self, secret: str, ttl_seconds: int) -> None:
        if len(secret) < 32:
            raise RuntimeError("WEBAPP_SESSION_SECRET must contain at least 32 characters")
        self.secret = secret.encode("utf-8")
        self.ttl_seconds = ttl_seconds

    def issue(self, telegram_user_id: int, now: int | None = None) -> str:
        issued_at = int(time.time()) if now is None else now
        payload = {
            "sub": telegram_user_id,
            "iat": issued_at,
            "exp": issued_at + self.ttl_seconds,
        }
        encoded = self._encode_json(payload)
        signature = self._sign(encoded)
        return f"{encoded}.{signature}"

    def verify(self, token: str, now: int | None = None) -> int:
        try:
            encoded, received_signature = token.split(".", 1)
        except ValueError as exc:
            raise WebAppAuthError("Session token is invalid") from exc
        if not hmac.compare_digest(self._sign(encoded), received_signature):
            raise WebAppAuthError("Session token signature is invalid")
        try:
            payload = self._decode_json(encoded)
            telegram_user_id = int(payload["sub"])
            expires_at = int(payload["exp"])
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise WebAppAuthError("Session token payload is invalid") from exc
        current_time = int(time.time()) if now is None else now
        if expires_at < current_time:
            raise WebAppAuthError("Session token has expired")
        return telegram_user_id

    def _sign(self, value: str) -> str:
        digest = hmac.new(self.secret, value.encode("ascii"), hashlib.sha256).digest()
        return self._base64url_encode(digest)

    @classmethod
    def _encode_json(cls, value: dict[str, Any]) -> str:
        raw = json.dumps(value, separators=(",", ":"), sort_keys=True).encode("utf-8")
        return cls._base64url_encode(raw)

    @staticmethod
    def _decode_json(value: str) -> dict[str, Any]:
        padding = "=" * (-len(value) % 4)
        raw = base64.urlsafe_b64decode(value + padding)
        decoded = json.loads(raw)
        if not isinstance(decoded, dict):
            raise WebAppAuthError("Session token payload is invalid")
        return decoded

    @staticmethod
    def _base64url_encode(value: bytes) -> str:
        return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")
