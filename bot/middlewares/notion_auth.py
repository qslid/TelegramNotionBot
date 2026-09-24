"""Inject Notion credentials into handler data when present."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from bot.database.db import try_session_factory
from bot.database.models import NotionCredential, User


class NotionAuthCheckMiddleware(BaseMiddleware):
    """Load `notion_credential` for the current user (may be None).

    Handlers that require Notion should check `data['notion_credential']`
    (or use the `@requires_notion` helper pattern) and prompt to connect.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        credential: NotionCredential | None = None
        db_user: User | None = data.get("db_user")
        session_factory = try_session_factory()

        if db_user is not None and session_factory is not None:
            async with session_factory() as session:
                result = await session.execute(
                    select(NotionCredential)
                    .where(NotionCredential.user_id == db_user.id)
                    .options(selectinload(NotionCredential.user))
                )
                credential = result.scalar_one_or_none()

        data["notion_credential"] = credential
        data["notion_connected"] = credential is not None
        return await handler(event, data)
