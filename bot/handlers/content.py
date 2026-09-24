"""Text / link → Notion page creation."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.database.models import NotionCredential
from bot.handlers.keyboards import main_menu_kb
from bot.handlers.states import NotionConnectFSM
from bot.locales import t
from bot.services.notion_service import NotionService

router = Router(name="content")


@router.message(F.text, ~F.text.startswith("/"))
async def handle_text_to_notion(
    message: Message,
    locale: str,
    state: FSMContext,
    notion_credential: NotionCredential | None,
) -> None:
    """Create a Notion page from plain text or links.

    Skips when an FSM connect wizard is active (token/db id entry).
    """
    current = await state.get_state()
    if current is not None and current.startswith(NotionConnectFSM.__name__):
        return  # Let the settings FSM handlers process this

    text = (message.text or "").strip()
    if not text:
        await message.answer(t("content.empty", locale))
        return

    if notion_credential is None:
        await message.answer(
            t("content.need_notion", locale),
            reply_markup=main_menu_kb(locale),
        )
        return

    status = await message.answer(t("content.saving", locale))
    service = NotionService(notion_credential.integration_token)
    result = await service.create_page_from_text(
        database_id=notion_credential.database_id,
        text=text,
        source=f"telegram:{message.from_user.id if message.from_user else 'unknown'}",
    )

    if result.ok:
        if result.page_url:
            await status.edit_text(t("content.saved", locale, url=result.page_url))
        else:
            await status.edit_text(t("content.saved_no_url", locale))
        return

    err = result.error or "notion_api_error"
    if err == "no_title_property":
        await status.edit_text(t("content.no_title_property", locale))
    else:
        # Prefer connect.* keys for known Notion errors, else generic
        key = f"connect.{err}"
        from bot.locales import _catalogs  # noqa: PLC0415

        if key not in (_catalogs.get(locale) or {}):
            await status.edit_text(t("content.error", locale, error=err))
        else:
            await status.edit_text(t(key, locale))
