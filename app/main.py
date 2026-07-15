from __future__ import annotations

import asyncio

from app.bot.app import build_bot, build_dispatcher
from app.core.config import get_settings
from app.core.logging import configure_logging


async def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    bot = build_bot(settings)
    dispatcher = build_dispatcher(settings)
    await dispatcher.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
