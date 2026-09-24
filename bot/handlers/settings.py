"""Settings, Connect Notion wizard, and Limits status."""

from __future__ import annotations

from datetime import datetime, timezone

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import delete, select

from bot.config import get_settings
from bot.database.db import get_session_factory
from bot.database.models import NotionCredential, User
from bot.handlers.keyboards import cancel_kb, main_menu_kb, settings_kb
from bot.handlers.states import NotionConnectFSM
from bot.locales import t
from bot.middlewares.usage import get_usage_snapshot
from bot.services.notion_service import NotionService

router = Router(name="settings")


def _settings_text(
    locale: str,
    *,
    connected: bool,
    workspace: str | None,
) -> str:
    lines = [
        t("settings.title", locale),
        t("settings.language", locale, language=locale),
    ]
    if connected:
        lines.append(
            t(
                "settings.notion_connected",
                locale,
                workspace=workspace or "—",
            )
        )
    else:
        lines.append(t("settings.notion_disconnected", locale))
    return "\n".join(lines)


@router.callback_query(F.data == "menu:settings")
async def open_settings(
    callback: CallbackQuery,
    locale: str,
    notion_credential: NotionCredential | None,
) -> None:
    connected = notion_credential is not None
    workspace = notion_credential.workspace_name if notion_credential else None
    await callback.message.edit_text(  # type: ignore[union-attr]
        _settings_text(locale, connected=connected, workspace=workspace),
        reply_markup=settings_kb(locale, connected=connected),
    )
    await callback.answer()


@router.callback_query(F.data == "menu:limits")
async def open_limits(
    callback: CallbackQuery,
    locale: str,
    db_user: User,
    notion_credential: NotionCredential | None,
) -> None:
    settings = get_settings()
    daily_used, monthly_used = await get_usage_snapshot(db_user.id)
    text = (
        t("limits.title", locale)
        + "\n"
        + t(
            "limits.body",
            locale,
            daily_used=daily_used,
            daily_limit=settings.daily_request_limit,
            monthly_used=monthly_used,
            monthly_limit=settings.monthly_request_limit,
        )
    )
    await callback.message.edit_text(  # type: ignore[union-attr]
        text,
        reply_markup=settings_kb(locale, connected=notion_credential is not None),
    )
    await callback.answer()


@router.callback_query(F.data == "menu:connect")
async def start_connect(
    callback: CallbackQuery,
    locale: str,
    state: FSMContext,
) -> None:
    await state.set_state(NotionConnectFSM.waiting_token)
    await callback.message.edit_text(  # type: ignore[union-attr]
        t("connect.ask_token", locale),
        reply_markup=cancel_kb(locale),
    )
    await callback.answer()


@router.callback_query(F.data == "connect:cancel")
async def cancel_connect(
    callback: CallbackQuery,
    locale: str,
    state: FSMContext,
    notion_connected: bool,
) -> None:
    await state.clear()
    key = "start.already_connected" if notion_connected else "start.welcome"
    await callback.message.edit_text(  # type: ignore[union-attr]
        t("connect.cancelled", locale) + "\n\n" + t(key, locale),
        reply_markup=main_menu_kb(locale),
    )
    await callback.answer()


@router.message(NotionConnectFSM.waiting_token, F.text)
async def receive_token(
    message: Message,
    locale: str,
    state: FSMContext,
) -> None:
    token = (message.text or "").strip()
    # Best-effort: delete the message containing the secret
    try:
        await message.delete()
    except Exception:
        pass

    if not token or len(token) < 10:
        await message.answer(
            t("connect.invalid_token", locale),
            reply_markup=cancel_kb(locale),
        )
        return

    await state.update_data(notion_token=token)
    await state.set_state(NotionConnectFSM.waiting_database_id)
    await message.answer(
        t("connect.ask_database", locale),
        reply_markup=cancel_kb(locale),
    )


@router.message(NotionConnectFSM.waiting_database_id, F.text)
async def receive_database_id(
    message: Message,
    locale: str,
    state: FSMContext,
    db_user: User,
) -> None:
    database_raw = (message.text or "").strip()
    data = await state.get_data()
    token = data.get("notion_token")
    if not token:
        await state.clear()
        await message.answer(t("connect.invalid_token", locale))
        return

    status = await message.answer(t("connect.validating", locale))
    service = NotionService(token)
    result = await service.validate_token_and_database(database_raw)

    if not result.ok:
        err_key = f"connect.{result.error}" if result.error else "connect.notion_api_error"
        # Fall back if key missing
        from bot.locales import _catalogs  # noqa: PLC0415

        if err_key not in (_catalogs.get(locale) or {}):
            err_key = "connect.notion_api_error"
        await status.edit_text(t(err_key, locale), reply_markup=cancel_kb(locale))
        return

    # Persist credentials
    from bot.services.notion_service import normalize_database_id  # noqa: PLC0415

    db_id = normalize_database_id(database_raw)
    session_factory = get_session_factory()
    async with session_factory() as session:
        existing = await session.execute(
            select(NotionCredential).where(NotionCredential.user_id == db_user.id)
        )
        cred = existing.scalar_one_or_none()
        now = datetime.now(timezone.utc)
        if cred is None:
            cred = NotionCredential(
                user_id=db_user.id,
                integration_token=token,
                database_id=db_id,
                workspace_name=result.workspace_name,
                validated_at=now,
            )
            session.add(cred)
        else:
            cred.integration_token = token
            cred.database_id = db_id
            cred.workspace_name = result.workspace_name
            cred.validated_at = now
        await session.commit()

    await state.clear()
    await status.edit_text(
        t(
            "connect.success",
            locale,
            workspace=result.workspace_name or "—",
            database=result.database_title or db_id,
        ),
        reply_markup=main_menu_kb(locale),
    )


@router.callback_query(F.data == "settings:disconnect")
async def disconnect_notion(
    callback: CallbackQuery,
    locale: str,
    db_user: User,
) -> None:
    session_factory = get_session_factory()
    async with session_factory() as session:
        await session.execute(
            delete(NotionCredential).where(NotionCredential.user_id == db_user.id)
        )
        await session.commit()

    await callback.message.edit_text(  # type: ignore[union-attr]
        t("settings.disconnected_ok", locale),
        reply_markup=main_menu_kb(locale),
    )
    await callback.answer()
