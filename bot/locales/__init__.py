"""i18n helpers: JSON locales with Telegram language_code detection."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_LOCALES_DIR = Path(__file__).resolve().parent
_SUPPORTED = ("en", "ru")
_catalogs: dict[str, dict[str, str]] = {}


def load_locales() -> None:
    """Load en/ru JSON catalogs into memory."""
    global _catalogs
    catalogs: dict[str, dict[str, str]] = {}
    for code in _SUPPORTED:
        path = _LOCALES_DIR / f"{code}.json"
        with path.open(encoding="utf-8") as fh:
            catalogs[code] = json.load(fh)
    _catalogs = catalogs
    logger.info("Loaded locales: %s", ", ".join(_catalogs))


def resolve_locale(language_code: str | None, default: str = "en") -> str:
    """Map Telegram language_code to supported locale (ru/en)."""
    if not language_code:
        return default if default in _SUPPORTED else "en"
    code = language_code.lower().split("-")[0]
    if code in _SUPPORTED:
        return code
    return default if default in _SUPPORTED else "en"


def t(key: str, locale: str = "en", **kwargs: Any) -> str:
    """Translate key for locale with optional str.format kwargs."""
    catalog = _catalogs.get(locale) or _catalogs.get("en") or {}
    template = catalog.get(key) or _catalogs.get("en", {}).get(key) or key
    if kwargs:
        try:
            return template.format(**kwargs)
        except (KeyError, ValueError):
            return template
    return template
