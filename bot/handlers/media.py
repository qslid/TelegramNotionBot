"""Media handlers (photo / document / video) — size check + upload stubs."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.types import Message

from bot.config import get_settings
from bot.database.models import NotionCredential
from bot.handlers.keyboards import main_menu_kb
from bot.locales import t

router = Router(name="media")


def _size_ok(file_size: int | None, max_bytes: int) -> bool:
    if file_size is None:
        # Unknown size — allow stub path but do not download
        return True
    return file_size < max_bytes


@router.message(F.photo)
async def handle_photo(
    message: Message,
    locale: str,
    notion_credential: NotionCredential | None,
) -> None:
    if notion_credential is None:
        await message.answer(
            t("media.need_notion", locale),
            reply_markup=main_menu_kb(locale),
        )
        return

    settings = get_settings()
    photo = message.photo[-1]  # largest
    size = photo.file_size or 0
    if not _size_ok(photo.file_size, settings.max_file_size_bytes):
        await message.answer(
            t(
                "media.too_large",
                locale,
                max_mb=settings.max_file_size_bytes // (1024 * 1024),
            )
        )
        return

    # TODO: download via Bot.get_file + upload to Notion file upload API
    #       or host externally and attach as external file URL.
    await message.answer(t("media.photo_stub", locale, size=size))


@router.message(F.document)
async def handle_document(
    message: Message,
    locale: str,
    notion_credential: NotionCredential | None,
) -> None:
    if notion_credential is None:
        await message.answer(
            t("media.need_notion", locale),
            reply_markup=main_menu_kb(locale),
        )
        return

    settings = get_settings()
    doc = message.document
    assert doc is not None
    size = doc.file_size or 0
    if not _size_ok(doc.file_size, settings.max_file_size_bytes):
        await message.answer(
            t(
                "media.too_large",
                locale,
                max_mb=settings.max_file_size_bytes // (1024 * 1024),
            )
        )
        return

    # TODO: download + upload to Notion / external URL attachment
    await message.answer(
        t(
            "media.document_stub",
            locale,
            name=doc.file_name or "file",
            size=size,
        )
    )


@router.message(F.video)
async def handle_video(
    message: Message,
    locale: str,
    notion_credential: NotionCredential | None,
) -> None:
    if notion_credential is None:
        await message.answer(
            t("media.need_notion", locale),
            reply_markup=main_menu_kb(locale),
        )
        return

    settings = get_settings()
    video = message.video
    assert video is not None
    size = video.file_size or 0
    if not _size_ok(video.file_size, settings.max_file_size_bytes):
        await message.answer(
            t(
                "media.too_large",
                locale,
                max_mb=settings.max_file_size_bytes // (1024 * 1024),
            )
        )
        return

    # TODO: download + upload to Notion / external URL attachment
    await message.answer(t("media.video_stub", locale, size=size))
