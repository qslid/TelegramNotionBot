"""Enforce and increment daily/monthly request counters per user."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import date
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject
from sqlalchemy import select

from bot.config import get_settings
from bot.database.db import try_session_factory
from bot.database.models import UsageCounter, User
from bot.locales import t


class UsageLimitMiddleware(BaseMiddleware):
    """Block content-creating messages when daily/monthly quotas are exceeded.

    Callbacks and /start-style commands are not counted; only Message events
    that look like user content (no leading / command) increment counters.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if isinstance(event, CallbackQuery):
            return await handler(event, data)

        if not isinstance(event, Message) or event.from_user is None:
            return await handler(event, data)

        # Don't count slash-commands against the quota
        text = event.text or event.caption or ""
        if text.startswith("/"):
            return await handler(event, data)

        # Don't count Notion connect wizard steps (token / database id)
        state = data.get("state")
        if state is not None:
            current = await state.get_state()
            if current and "NotionConnectFSM" in current:
                return await handler(event, data)

        db_user: User | None = data.get("db_user")
        session_factory = try_session_factory()
        if db_user is None or session_factory is None:
            return await handler(event, data)

        settings = get_settings()
        locale = data.get("locale", "en")
        today = date.today()
        day_key = today.isoformat()
        month_key = today.strftime("%Y-%m")

        async with session_factory() as session:
            daily = await _get_or_create(session, db_user.id, "day", day_key)
            monthly = await _get_or_create(session, db_user.id, "month", month_key)

            if daily.request_count >= settings.daily_request_limit:
                await event.answer(
                    t("limits.daily_exceeded", locale, limit=settings.daily_request_limit)
                )
                return None
            if monthly.request_count >= settings.monthly_request_limit:
                await event.answer(
                    t(
                        "limits.monthly_exceeded",
                        locale,
                        limit=settings.monthly_request_limit,
                    )
                )
                return None

            daily.request_count += 1
            monthly.request_count += 1
            await session.commit()

            data["usage_daily"] = daily.request_count
            data["usage_monthly"] = monthly.request_count

        return await handler(event, data)


async def _get_or_create(
    session: Any,
    user_id: int,
    period_type: str,
    period_key: str,
) -> UsageCounter:
    result = await session.execute(
        select(UsageCounter).where(
            UsageCounter.user_id == user_id,
            UsageCounter.period_type == period_type,
            UsageCounter.period_key == period_key,
        )
    )
    row = result.scalar_one_or_none()
    if row is None:
        row = UsageCounter(
            user_id=user_id,
            period_type=period_type,
            period_key=period_key,
            request_count=0,
        )
        session.add(row)
        await session.flush()
    return row


async def get_usage_snapshot(user_id: int) -> tuple[int, int]:
    """Return (daily_used, monthly_used) for display in Settings / Limits."""
    session_factory = try_session_factory()
    if session_factory is None:
        return 0, 0
    today = date.today()
    day_key = today.isoformat()
    month_key = today.strftime("%Y-%m")
    async with session_factory() as session:
        daily = await session.execute(
            select(UsageCounter).where(
                UsageCounter.user_id == user_id,
                UsageCounter.period_type == "day",
                UsageCounter.period_key == day_key,
            )
        )
        monthly = await session.execute(
            select(UsageCounter).where(
                UsageCounter.user_id == user_id,
                UsageCounter.period_type == "month",
                UsageCounter.period_key == month_key,
            )
        )
        d = daily.scalar_one_or_none()
        m = monthly.scalar_one_or_none()
        return (d.request_count if d else 0), (m.request_count if m else 0)
