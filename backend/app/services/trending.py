from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from app.database.session import get_db_context
from app.models.query_log import QueryLog as DBQueryLog
from app.models.schemas import Citation, TrendCandidate, TrendPin
from app.services.retrieval import embed_text


def safe_parse_uuid(val: Any) -> uuid.UUID | None:
    if not val:
        return None
    if isinstance(val, uuid.UUID):
        return val
    cleaned = str(val).replace("session-", "").replace("ticket-", "").replace("usr-", "").replace("user-", "")
    try:
        return uuid.UUID(cleaned)
    except ValueError:
        return uuid.uuid5(uuid.NAMESPACE_DNS, cleaned)


@dataclass
class QueryLog:
    message_id: str
    user_id: str
    query: str
    topic_key: str
    answer: str | None
    citations: list[Citation]
    created_at: datetime


_QUERY_LOGS: list[QueryLog] = []
_MESSAGE_IDS: set[str] = set()
_CANDIDATES: list[TrendCandidate] = []
_PINS: list[TrendPin] = []


async def record_chat_query(
    message_id: str,
    user_id: str,
    query: str,
    citations: list[Citation],
    session_id: str | None = None,
    answer: str | None = None,
) -> None:
    _MESSAGE_IDS.add(message_id)
    topic = topic_key(query)
    _QUERY_LOGS.append(
        QueryLog(
            message_id=message_id,
            user_id=user_id,
            query=query,
            topic_key=topic,
            answer=answer,
            citations=citations,
            created_at=datetime.now(timezone.utc),
        )
    )

    user_uuid = safe_parse_uuid(user_id)
    session_uuid = safe_parse_uuid(session_id)

    if session_uuid and user_uuid:
        from app.models.chat import ChatSession

        try:
            async with get_db_context() as session:
                db_session = await session.get(ChatSession, session_uuid)
                if not db_session:
                    db_session = ChatSession(id=session_uuid, user_id=user_uuid, title="Chat Session")
                    session.add(db_session)
                    await session.commit()
        except Exception as e:
            print(f"Error ensuring session exists: {e}")

    db_log = DBQueryLog(
        user_id=user_uuid,
        session_id=session_uuid,
        question=query,
        normalized_question=query.strip().lower(),
        intent="ask_policy",
        topic=topic,
        department="HR",
    )

    try:
        async with get_db_context() as session:
            session.add(db_log)
            await session.commit()
    except Exception as e:
        print(f"Error logging query to DB: {e}")


def message_exists(message_id: str) -> bool:
    return message_id in _MESSAGE_IDS


def run_trending(window_minutes: int = 60, threshold: int = 5) -> tuple[list[TrendCandidate], list[str]]:
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=window_minutes)
    grouped: dict[str, list[QueryLog]] = {}
    for item in _QUERY_LOGS:
        if item.created_at >= cutoff:
            grouped.setdefault(item.topic_key, []).append(item)

    created: list[TrendCandidate] = []
    skipped: list[str] = []
    pinned_topics = {pin.topic_key for pin in _PINS}
    draft_topics = {candidate.topic_key for candidate in _CANDIDATES}
    for key, items in grouped.items():
        if len(items) < threshold:
            skipped.append(key)
            continue
        if key in pinned_topics or key in draft_topics:
            skipped.append(key)
            continue

        title = _title_for_topic(key)
        citations = _first_citations(items)
        summary = _build_trend_answer_summary(title=title, items=items, citations=citations)
        candidate = TrendCandidate(
            id=f"candidate-{uuid4()}",
            topic_key=key,
            title=title,
            summary=summary,
            source_query_count=len(items),
            citations=citations,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        _CANDIDATES.append(candidate)
        created.append(candidate)
        draft_topics.add(key)
    return created, skipped


def list_trend_candidates() -> list[TrendCandidate]:
    return list(_CANDIDATES)


def approve_trend_candidate(candidate_id: str) -> TrendPin | None:
    candidate = next((item for item in _CANDIDATES if item.id == candidate_id), None)
    if candidate is None:
        return None

    existing_pin = next((pin for pin in _PINS if pin.topic_key == candidate.topic_key), None)
    _CANDIDATES.remove(candidate)
    if existing_pin is not None:
        return existing_pin

    pin = TrendPin(
        id=f"pin-{uuid4()}",
        topic_key=candidate.topic_key,
        title=candidate.title,
        summary=candidate.summary,
        source_query_count=candidate.source_query_count,
        citations=candidate.citations,
        created_at=datetime.now(timezone.utc).isoformat(),
        expires_at=None,
    )
    _PINS.append(pin)
    return pin


def list_trend_pins() -> list[TrendPin]:
    return list(_PINS)


def reset_trending_store() -> None:
    _QUERY_LOGS.clear()
    _MESSAGE_IDS.clear()
    _CANDIDATES.clear()
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


def _build_trend_answer_summary(*, title: str, items: list[QueryLog], citations: list[Citation]) -> str:
    topic_name = _display_title(title)
    question_examples = _unique_values(item.query for item in items)[:3]
    answer_examples = _unique_values(item.answer or "" for item in items if item.answer)[:3]

    if citations:
        source = citations[0]
        source_label = source.document_title
        if source.section:
            source_label = f"{source_label} - {source.section}"
        supported_text = _compact_text(source.excerpt, max_len=420)
        summary = (
            f"Tóm tắt câu trả lời cho chủ đề {topic_name}: {supported_text} "
            f"Nguồn tham khảo chính: {source_label}."
        )
    elif answer_examples:
        combined_answer = _compact_text(" ".join(answer_examples), max_len=520)
        summary = f"Tóm tắt câu trả lời cho chủ đề {topic_name}: {combined_answer}"
    else:
        summary = (
            f"Chủ đề {topic_name} đang được nhiều nhân viên hỏi. "
            "Chưa có đủ câu trả lời có nguồn để tóm tắt, HR nên bổ sung tài liệu hoặc phản hồi chuẩn."
        )

    if question_examples:
        summary += " Câu hỏi thường gặp: " + "; ".join(question_examples) + "."
    return summary


def _unique_values(values) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for value in values:
        normalized = " ".join(str(value).split())
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        unique.append(normalized)
    return unique


def _compact_text(text: str, *, max_len: int) -> str:
    compacted = " ".join(text.split())
    if len(compacted) <= max_len:
        return compacted
    return compacted[: max_len - 3].rstrip() + "..."
