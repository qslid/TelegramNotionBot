"""Reject oversized media before any download attempt."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject

from bot.config import get_settings
from bot.locales import t


class FileSizeLimitMiddleware(BaseMiddleware):
    """Enforce file_size < MAX_FILE_SIZE_BYTES for photo / document / video."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if not isinstance(event, Message):
            return await handler(event, data)

        settings = get_settings()
        max_bytes = settings.max_file_size_bytes
        size: int | None = None

        if event.photo:
            size = event.photo[-1].file_size
        elif event.document is not None:
            size = event.document.file_size
        elif event.video is not None:
            size = event.video.file_size
        else:
            return await handler(event, data)

        if size is not None and size >= max_bytes:
            locale = data.get("locale", "en")
            await event.answer(
                t(
                    "media.too_large",
                    locale,
                    max_mb=max_bytes // (1024 * 1024),
                )
            )
            return None

        return await handler(event, data)
