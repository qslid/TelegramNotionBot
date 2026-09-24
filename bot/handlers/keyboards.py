"""Reusable inline keyboards."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.locales import t


def main_menu_kb(locale: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t("menu.settings", locale),
                    callback_data="menu:settings",
                )
            ],
            [
                InlineKeyboardButton(
                    text=t("menu.connect_notion", locale),
                    callback_data="menu:connect",
                )
            ],
            [
                InlineKeyboardButton(
                    text=t("menu.limits", locale),
                    callback_data="menu:limits",
                )
            ],
        ]
    )


def settings_kb(locale: str, *, connected: bool) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = [
        [
            InlineKeyboardButton(
                text=t("menu.connect_notion", locale),
                callback_data="menu:connect",
            )
        ],
        [
            InlineKeyboardButton(
                text=t("menu.limits", locale),
                callback_data="menu:limits",
            )
        ],
    ]
    if connected:
        rows.append(
            [
                InlineKeyboardButton(
                    text=t("settings.disconnect", locale),
                    callback_data="settings:disconnect",
                )
            ]
        )
    rows.append(
        [
            InlineKeyboardButton(
                text=t("menu.back", locale),
                callback_data="menu:home",
            )
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def cancel_kb(locale: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t("connect.cancel_btn", locale),
                    callback_data="connect:cancel",
                )
            ]
        ]
    )
