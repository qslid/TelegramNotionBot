"""Per-user message throttling: ≤1 message / N seconds."""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject

from bot.config import get_settings
from bot.locales import t


class ThrottlingMiddleware(BaseMiddleware):
    """Drop (answer + skip) messages arriving faster than the configured rate."""

    def __init__(self, rate_seconds: float | None = None) -> None:
        self.rate_seconds = rate_seconds if rate_seconds is not None else get_settings().throttle_rate_seconds
        self._last_seen: dict[int, float] = {}

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if not isinstance(event, Message) or event.from_user is None:
            return await handler(event, data)

        user_id = event.from_user.id
        now = time.monotonic()
        last = self._last_seen.get(user_id)
        if last is not None and (now - last) < self.rate_seconds:
            locale = data.get("locale", "en")
            await event.answer(
                t("throttle.slow_down", locale, seconds=int(self.rate_seconds))
            )
            return None

        self._last_seen[user_id] = now
        # Soft cleanup to avoid unbounded growth
        if len(self._last_seen) > 10_000:
            cutoff = now - self.rate_seconds * 10
            self._last_seen = {k: v for k, v in self._last_seen.items() if v >= cutoff}

        return await handler(event, data)
