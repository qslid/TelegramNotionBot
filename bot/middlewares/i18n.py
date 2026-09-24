"""Detect locale from Telegram language_code and ensure User row exists."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject
from sqlalchemy import select

from bot.config import get_settings
from bot.database.db import try_session_factory
from bot.database.models import User
from bot.locales import resolve_locale


class I18nMiddleware(BaseMiddleware):
    """Inject `locale` and `db_user` into handler data; upsert User.language."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        from_user = None
        if isinstance(event, Message):
            from_user = event.from_user
        elif isinstance(event, CallbackQuery):
            from_user = event.from_user

        settings = get_settings()
        locale = settings.default_locale
        db_user: User | None = None
        session_factory = try_session_factory()

        if from_user is not None and session_factory is not None:
            locale = resolve_locale(from_user.language_code, settings.default_locale)
            async with session_factory() as session:
                result = await session.execute(
                    select(User).where(User.telegram_id == from_user.id)
                )
                db_user = result.scalar_one_or_none()
                if db_user is None:
                    db_user = User(
                        telegram_id=from_user.id,
                        username=from_user.username,
                        language=locale,
                    )
                    session.add(db_user)
                    await session.commit()
                    await session.refresh(db_user)
                else:
                    # Keep language in sync with Telegram preference
                    changed = False
                    if db_user.language != locale:
                        db_user.language = locale
                        changed = True
                    if from_user.username and db_user.username != from_user.username:
                        db_user.username = from_user.username
                        changed = True
                    if changed:
                        await session.commit()
                        await session.refresh(db_user)

        data["locale"] = locale
        data["db_user"] = db_user
        return await handler(event, data)
