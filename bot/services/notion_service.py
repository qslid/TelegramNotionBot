"""Notion API service: token validation and page/row creation."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

import httpx
from notion_client import AsyncClient
from notion_client.errors import APIResponseError

logger = logging.getLogger(__name__)

# Notion IDs may be UUID with or without dashes, sometimes prefixed with a title slug.
_UUID_RE = re.compile(
    r"[0-9a-fA-F]{8}-?[0-9a-fA-F]{4}-?[0-9a-fA-F]{4}-?[0-9a-fA-F]{4}-?[0-9a-fA-F]{12}"
)


@dataclass(frozen=True, slots=True)
class NotionValidationResult:
    """Outcome of validating an integration token + database id."""

    ok: bool
    workspace_name: Optional[str] = None
    database_title: Optional[str] = None
    error: Optional[str] = None


@dataclass(frozen=True, slots=True)
class NotionPageResult:
    """Outcome of creating a Notion page."""

    ok: bool
    page_id: Optional[str] = None
    page_url: Optional[str] = None
    error: Optional[str] = None


def normalize_database_id(raw: str) -> str:
    """Extract a dashed UUID from a pasted Notion URL or bare id."""
    text = raw.strip()
    match = _UUID_RE.search(text)
    if not match:
        raise ValueError("invalid_database_id")
    hex_id = match.group(0).replace("-", "")
    return str(UUID(hex_id))


class NotionService:
    """Thin async wrapper around notion-client / httpx."""

    def __init__(self, token: str, *, timeout: float = 30.0) -> None:
        self._token = token.strip()
        self._timeout = timeout

    def _client(self) -> AsyncClient:
        return AsyncClient(auth=self._token, client=httpx.AsyncClient(timeout=self._timeout))

    async def validate_token_and_database(self, database_id: str) -> NotionValidationResult:
        """Check that the token works and the integration can see the database."""
        try:
            db_id = normalize_database_id(database_id)
        except ValueError:
            return NotionValidationResult(ok=False, error="invalid_database_id")

        client = self._client()
        try:
            me = await client.users.me()
            workspace_name = None
            if isinstance(me, dict):
                bot = me.get("bot") or {}
                owner = bot.get("owner") or {}
                workspace = owner.get("workspace") or {}
                workspace_name = workspace.get("name") or me.get("name")

            database = await client.databases.retrieve(database_id=db_id)
            title = _extract_title(database)
            return NotionValidationResult(
                ok=True,
                workspace_name=workspace_name,
                database_title=title,
            )
        except APIResponseError as exc:
            logger.warning("Notion validation failed: %s", exc)
            return NotionValidationResult(ok=False, error=_map_api_error(exc))
        except httpx.HTTPError as exc:
            logger.exception("Notion HTTP error during validation")
            return NotionValidationResult(ok=False, error="network_error")
        finally:
            await client.aclose()

    async def create_page_from_text(
        self,
        *,
        database_id: str,
        text: str,
        source: str = "telegram",
    ) -> NotionPageResult:
        """Create a database row / page with the given text as title + body.

        Uses a flexible property map: prefers a title property named Name/Title/Название,
        otherwise the first title property on the database schema.
        """
        try:
            db_id = normalize_database_id(database_id)
        except ValueError:
            return NotionPageResult(ok=False, error="invalid_database_id")

        title_text = _title_from_text(text)
        body = text.strip()
        client = self._client()
        try:
            database = await client.databases.retrieve(database_id=db_id)
            title_prop = _find_title_property(database)
            if not title_prop:
                return NotionPageResult(ok=False, error="no_title_property")

            properties: dict[str, Any] = {
                title_prop: {"title": [{"type": "text", "text": {"content": title_text[:2000]}}]},
            }
            # Optional rich-text / URL columns if present (best-effort, ignore if missing)
            props = (database.get("properties") or {}) if isinstance(database, dict) else {}
            if "Source" in props and props["Source"].get("type") == "rich_text":
                properties["Source"] = {
                    "rich_text": [{"type": "text", "text": {"content": source}}],
                }
            if "URL" in props and props["URL"].get("type") == "url":
                url = _first_url(body)
                if url:
                    properties["URL"] = {"url": url}

            children = [
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {"content": chunk},
                            }
                        ]
                    },
                }
                for chunk in _chunk_text(body, 1900)
            ]
            # Stamp when the bot created the entry
            children.append(
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": (
                                        f"⏱ {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}"
                                        f" · via {source}"
                                    )
                                },
                                "annotations": {"italic": True, "color": "gray"},
                            }
                        ]
                    },
                }
            )

            page = await client.pages.create(
                parent={"database_id": db_id},
                properties=properties,
                children=children[:100],  # Notion limit per request
            )
            page_id = page.get("id") if isinstance(page, dict) else None
            page_url = page.get("url") if isinstance(page, dict) else None
            return NotionPageResult(ok=True, page_id=page_id, page_url=page_url)
        except APIResponseError as exc:
            logger.warning("Notion page create failed: %s", exc)
            return NotionPageResult(ok=False, error=_map_api_error(exc))
        except httpx.HTTPError:
            logger.exception("Notion HTTP error during page create")
            return NotionPageResult(ok=False, error="network_error")
        finally:
            await client.aclose()


def _extract_title(database: Any) -> Optional[str]:
    if not isinstance(database, dict):
        return None
    title_parts = database.get("title") or []
    texts = [p.get("plain_text", "") for p in title_parts if isinstance(p, dict)]
    joined = "".join(texts).strip()
    return joined or None


def _find_title_property(database: Any) -> Optional[str]:
    if not isinstance(database, dict):
        return None
    props: dict[str, Any] = database.get("properties") or {}
    preferred = ("Name", "Title", "Название", "Имя", "name", "title")
    for name in preferred:
        prop = props.get(name)
        if prop and prop.get("type") == "title":
            return name
    for name, prop in props.items():
        if isinstance(prop, dict) and prop.get("type") == "title":
            return name
    return None


def _title_from_text(text: str) -> str:
    line = text.strip().splitlines()[0] if text.strip() else "Untitled"
    line = line.strip()
    if len(line) > 100:
        return line[:97] + "…"
    return line or "Untitled"


def _first_url(text: str) -> Optional[str]:
    match = re.search(r"https?://\S+", text)
    return match.group(0).rstrip(").,]}>\"'") if match else None


def _chunk_text(text: str, size: int) -> list[str]:
    if not text:
        return [" "]
    return [text[i : i + size] for i in range(0, len(text), size)]


def _map_api_error(exc: APIResponseError) -> str:
    code = getattr(exc, "code", None) or ""
    status = getattr(exc, "status", None)
    if status == 401 or code in {"unauthorized", "invalid_api_key"}:
        return "invalid_token"
    if status == 404 or code in {"object_not_found"}:
        return "database_not_found"
    if status == 403 or code in {"restricted_resource"}:
        return "no_access"
    return "notion_api_error"
