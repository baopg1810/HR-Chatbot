from __future__ import annotations

import html
import logging
from typing import Any

import httpx

from app.core.config import get_settings
from app.database.session import get_db_context
from app.models.schemas import ChatResponse, TrendPin
from app.services.telegram_links import deactivate_telegram_link, list_active_telegram_links

logger = logging.getLogger(__name__)

TELEGRAM_API_BASE = "https://api.telegram.org"
MAX_TELEGRAM_MESSAGE_LENGTH = 4096


class TelegramBotError(RuntimeError):
    pass


async def send_telegram_message(chat_id: int, text: str, *, parse_mode: str | None = None) -> dict[str, Any] | None:
    settings = get_settings()
    if not settings.telegram_bot_token:
        logger.info("telegram_bot_token_missing")
        return None

    payload: dict[str, Any] = {
        "chat_id": chat_id,
        "text": _clip_message(text),
        "disable_web_page_preview": True,
    }
    if parse_mode:
        payload["parse_mode"] = parse_mode

    url = f"{TELEGRAM_API_BASE}/bot{settings.telegram_bot_token}/sendMessage"
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(url, json=payload)
    if response.status_code >= 400:
        raise TelegramBotError(f"Telegram sendMessage failed: {response.status_code} {response.text[:200]}")
    data = response.json()
    if not data.get("ok"):
        raise TelegramBotError(f"Telegram sendMessage returned ok=false: {data}")
    return data


async def broadcast_trend_pin(pin: TrendPin) -> None:
    settings = get_settings()
    if not settings.telegram_broadcast_enabled:
        return

    message = format_trending_pin_message(pin, app_url=settings.telegram_app_url)
    async with get_db_context() as db:
        links = await list_active_telegram_links(db)
        for link in links:
            try:
                await send_telegram_message(link.telegram_chat_id, message, parse_mode="HTML")
            except Exception as exc:
                logger.warning("telegram_trend_pin_send_failed", extra={"chat_id": link.telegram_chat_id, "error": str(exc)})
                if _is_forbidden_telegram_error(exc):
                    await deactivate_telegram_link(db, link.telegram_chat_id)


def format_chat_response_for_telegram(response: ChatResponse, *, app_url: str = "") -> str:
    parts = [response.answer.strip() or "Mình chưa có câu trả lời phù hợp."]
    if response.citations:
        sources = []
        for citation in response.citations[:3]:
            title = getattr(citation, "document_title", None)
            section = getattr(citation, "section", None)
            if title and section:
                sources.append(f"{title} - {section}")
            elif title:
                sources.append(title)
        if sources:
            parts.append("Nguồn: " + "; ".join(sources))

    if _requires_web_confirmation(response):
        suffix = "Để xác nhận hoặc gửi yêu cầu, vui lòng mở HR Assistant"
        if app_url:
            suffix += f": {app_url}"
        parts.append(suffix)
    return _clip_message("\n\n".join(parts))


def format_trending_pin_message(pin: TrendPin, *, app_url: str = "") -> str:
    title = html.escape(pin.title)
    summary = html.escape(pin.summary)
    parts = [
        "<b>📌 Chủ đề đang được quan tâm</b>",
        f"<b>{title}</b>",
        summary,
        f"Có {pin.source_query_count} câu hỏi gần đây về chủ đề này.",
    ]
    if pin.citations:
        source = pin.citations[0]
        source_title = html.escape(source.document_title)
        parts.append(f"Nguồn: {source_title}")
    if app_url:
        parts.append(f'<a href="{html.escape(app_url)}">Mở HR Assistant</a>')
    return _clip_message("\n\n".join(parts))


def _requires_web_confirmation(response: ChatResponse) -> bool:
    return any(
        action.type in {"ticket_draft_confirmation", "escalation_confirmation_required"}
        for action in response.actions
    )


def _clip_message(text: str) -> str:
    if len(text) <= MAX_TELEGRAM_MESSAGE_LENGTH:
        return text
    return text[: MAX_TELEGRAM_MESSAGE_LENGTH - 3].rstrip() + "..."


def _is_forbidden_telegram_error(exc: Exception) -> bool:
    text = str(exc).lower()
    return "403" in text or "bot was blocked" in text or "forbidden" in text
