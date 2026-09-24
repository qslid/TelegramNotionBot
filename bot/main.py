"""Telegram bot entrypoint: wire DB, middlewares, routers, and long-polling."""

from __future__ import annotations

import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from bot.config import get_settings
from bot.database.db import dispose_db, init_db
from bot.handlers import setup_routers
from bot.locales import load_locales
from bot.middlewares import (
    FileSizeLimitMiddleware,
    I18nMiddleware,
    NotionAuthCheckMiddleware,
    ThrottlingMiddleware,
    UsageLimitMiddleware,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("bot")


async def main() -> None:
    settings = get_settings()
    load_locales()
    await init_db()

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())

    # Middleware order: throttle → i18n/user → file size → usage → notion auth
    for observer in (dp.message, dp.callback_query):
        observer.middleware(ThrottlingMiddleware())
        observer.middleware(I18nMiddleware())
        observer.middleware(NotionAuthCheckMiddleware())

    dp.message.middleware(FileSizeLimitMiddleware())
    dp.message.middleware(UsageLimitMiddleware())

    dp.include_router(setup_routers())

    logger.info("Bot starting (polling)…")
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await dispose_db()
        await bot.session.close()
        logger.info("Bot stopped.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Interrupted.")
