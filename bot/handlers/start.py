""" /start and home menu handlers."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, Message

from bot.database.models import NotionCredential, User
from bot.handlers.keyboards import main_menu_kb
from bot.locales import t

router = Router(name="start")


@router.message(CommandStart())
async def cmd_start(
    message: Message,
    locale: str,
    notion_connected: bool,
) -> None:
    key = "start.already_connected" if notion_connected else "start.welcome"
    await message.answer(t(key, locale), reply_markup=main_menu_kb(locale))


@router.callback_query(F.data == "menu:home")
async def menu_home(
    callback: CallbackQuery,
    locale: str,
    notion_connected: bool,
) -> None:
    key = "start.already_connected" if notion_connected else "start.welcome"
    await callback.message.edit_text(  # type: ignore[union-attr]
        t(key, locale),
        reply_markup=main_menu_kb(locale),
    )
    await callback.answer()
