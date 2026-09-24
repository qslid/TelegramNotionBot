"""Telegram update handlers."""

from aiogram import Router

from bot.handlers import content, media, settings, start


def setup_routers() -> Router:
    """Compose and return the root router with all feature routers."""
    root = Router(name="root")
    root.include_router(start.router)
    root.include_router(settings.router)
    root.include_router(content.router)
    root.include_router(media.router)
    return root
