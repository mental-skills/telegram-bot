from __future__ import annotations

from collections import defaultdict, deque
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject


class InMemoryRateLimitMiddleware(BaseMiddleware):
    def __init__(self, messages_per_minute: int) -> None:
        self.messages_per_minute = messages_per_minute
        self._events: dict[int, deque[datetime]] = defaultdict(deque)

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, object]], Awaitable[object]],
        event: TelegramObject,
        data: dict[str, object],
    ) -> object | None:
        user = data.get("event_from_user")
        user_id = getattr(user, "id", None)
        if user_id is None:
            return await handler(event, data)

        now = datetime.now(UTC)
        window = now - timedelta(minutes=1)
        events = self._events[int(user_id)]
        while events and events[0] < window:
            events.popleft()
        if len(events) >= self.messages_per_minute:
            return None
        events.append(now)
        return await handler(event, data)
