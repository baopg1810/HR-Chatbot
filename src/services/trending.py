from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from src.models.schemas import Citation, TrendPin
from src.services.retrieval import embed_text


@dataclass
class QueryLog:
    message_id: str
    user_id: str
    query: str
    topic_key: str
    citations: list[Citation]
    created_at: datetime


_QUERY_LOGS: list[QueryLog] = []
_MESSAGE_IDS: set[str] = set()
_PINS: list[TrendPin] = []


def record_chat_query(message_id: str, user_id: str, query: str, citations: list[Citation]) -> None:
    _MESSAGE_IDS.add(message_id)
    _QUERY_LOGS.append(
        QueryLog(
            message_id=message_id,
            user_id=user_id,
            query=query,
            topic_key=topic_key(query),
            citations=citations,
            created_at=datetime.now(timezone.utc),
        )
    )


def message_exists(message_id: str) -> bool:
    return message_id in _MESSAGE_IDS


def run_trending(window_minutes: int = 60, threshold: int = 5) -> tuple[list[TrendPin], list[str]]:
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=window_minutes)
    grouped: dict[str, list[QueryLog]] = {}
    for item in _QUERY_LOGS:
        if item.created_at >= cutoff:
            grouped.setdefault(item.topic_key, []).append(item)

    created: list[TrendPin] = []
    skipped: list[str] = []
    existing_topics = {pin.title for pin in _PINS}
    for key, items in grouped.items():
        if len(items) < threshold:
            skipped.append(key)
            continue
        title = _title_for_topic(key)
        if title in existing_topics:
            skipped.append(key)
            continue
        citations = _first_citations(items)
        pin = TrendPin(
            id=f"pin-{uuid4()}",
            title=title,
            summary=f"Có {len(items)} câu hỏi gần đây về {_display_title(title).lower()}. HR nên ghim câu trả lời chung cho chủ đề này.",
            source_query_count=len(items),
            citations=citations,
            created_at=datetime.now(timezone.utc).isoformat(),
            expires_at=None,
        )
        _PINS.append(pin)
        created.append(pin)
        existing_topics.add(title)
    return created, skipped


def list_trend_pins() -> list[TrendPin]:
    return list(_PINS)


def reset_trending_store() -> None:
    _QUERY_LOGS.clear()
    _MESSAGE_IDS.clear()
    _PINS.clear()


def topic_key(query: str) -> str:
    tokens = set(embed_text(query))
    if {"nghi", "phep"} <= tokens or {"leave"} <= tokens:
        return "nghi-phep"
    if {"bao", "hiem"} <= tokens or {"insurance"} <= tokens:
        return "bao-hiem"
    if {"luong"} <= tokens or {"salary"} <= tokens:
        return "luong"
    if {"khen", "thuong"} <= tokens or {"reward"} <= tokens:
        return "khen-thuong"
    meaningful = sorted(token for token in tokens if token not in {"toi", "can", "hoi", "ve", "la", "gi", "nhan", "vien"})
    return "-".join(meaningful[:3]) or "khac"


def _title_for_topic(key: str) -> str:
    titles = {
        "nghi-phep": "Nghỉ phép",
        "bao-hiem": "Bảo hiểm",
        "luong": "Lương",
        "khen-thuong": "Khen thưởng",
    }
    return titles.get(key, key.replace("-", " ").title())


def _display_title(title: str) -> str:
    titles = {
        "Bao hiem": "Bảo hiểm",
        "Bảo hiểm": "Bảo hiểm",
        "Khen thuong": "Khen thưởng",
        "Khen thưởng": "Khen thưởng",
        "Luong": "Lương",
        "Lương": "Lương",
        "Nghi phep": "Nghỉ phép",
        "Nghỉ phép": "Nghỉ phép",
    }
    return titles.get(title, title)


def _first_citations(items: list[QueryLog]) -> list[Citation]:
    for item in items:
        if item.citations:
            return item.citations
    return []
