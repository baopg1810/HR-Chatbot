from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from app.database.session import get_db_context
from app.models.query_log import QueryLog as DBQueryLog
from app.models.schemas import Citation, TrendCandidate, TrendPin
from app.services.llm import generate_text
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


@dataclass
class TrendDraftContent:
    title: str
    summary: str


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

        citations = _first_citations(items)
        draft_content = _build_trend_draft_content(topic_key=key, items=items, citations=citations)
        candidate = TrendCandidate(
            id=f"candidate-{uuid4()}",
            topic_key=key,
            title=draft_content.title,
            summary=draft_content.summary,
            source_query_count=len(items),
            citations=citations,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        _CANDIDATES.append(candidate)
        created.append(candidate)
        draft_topics.add(key)
    return created, skipped


def list_trend_candidates() -> list[TrendCandidate]:
    return [_sanitize_trend_candidate(candidate) for candidate in _CANDIDATES]


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
    return [_sanitize_trend_pin(pin) for pin in _PINS]


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
    if {"dao", "tao"} <= tokens or {"phat", "trien"} <= tokens or {"training"} <= tokens or {"development"} <= tokens:
        return "dao-tao-phat-trien"
    meaningful = [
        token
        for token in embed_text(query)
        if token
        not in {
            "toi",
            "can",
            "hoi",
            "ve",
            "la",
            "gi",
            "nhan",
            "vien",
            "nhu",
            "the",
            "nao",
            "duoc",
            "chinh",
            "thuc",
        }
    ]
    return "-".join(meaningful[:3]) or "khac"


def _title_for_topic(key: str) -> str:
    titles = {
        "nghi-phep": "Nghỉ phép",
        "bao-hiem": "Bảo hiểm",
        "luong": "Lương",
        "khen-thuong": "Khen thưởng",
        "dao-tao-phat-trien": "Đào tạo và phát triển",
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


def _build_trend_draft_content(*, topic_key: str, items: list[QueryLog], citations: list[Citation]) -> TrendDraftContent:
    fallback_title = _title_for_topic(topic_key)
    fallback_summary = _build_trend_answer_summary(title=fallback_title, items=items, citations=citations)
    llm_content = _build_llm_trend_draft_content(
        fallback_title=fallback_title,
        fallback_summary=fallback_summary,
        items=items,
        citations=citations,
    )
    return llm_content or TrendDraftContent(title=fallback_title, summary=fallback_summary)


def _build_llm_trend_draft_content(
    *,
    fallback_title: str,
    fallback_summary: str,
    items: list[QueryLog],
    citations: list[Citation],
) -> TrendDraftContent | None:
    prompt = _build_trend_prompt(items=items, citations=citations)
    try:
        generated = generate_text(prompt)
    except Exception as exc:
        print(f"Warning: LLM trend draft failed, falling back to local summary: {exc}")
        return None
    if not generated:
        return None

    data = _parse_trend_json(generated)
    if not data:
        return None

    title = _clean_llm_trend_text(str(data.get("title") or ""))
    summary = _clean_llm_trend_text(str(data.get("summary") or ""))
    if not title or len(title) > 80:
        title = fallback_title
    if not summary or len(summary) > 900:
        summary = fallback_summary
    return TrendDraftContent(title=title, summary=summary)


def _build_trend_prompt(*, items: list[QueryLog], citations: list[Citation]) -> str:
    questions = "\n".join(f"- {query}" for query in _unique_values(item.query for item in items)[:8])
    answers = "\n".join(f"- {_compact_text(answer, max_len=360)}" for answer in _unique_values(item.answer or "" for item in items if item.answer)[:4])
    source_blocks = []
    for index, citation in enumerate(citations[:3], start=1):
        source_blocks.append(
            f"[{index}] Tài liệu: {citation.document_title}\n"
            f"Nội dung: {_compact_text(citation.excerpt, max_len=520)}"
        )
    sources = "\n\n".join(source_blocks) or "Không có nguồn trích dẫn."
    answer_block = answers or "Không có câu trả lời mẫu."
    return (
        "Bạn là HR analyst. Hãy tạo nội dung TrendPin cho nhóm câu hỏi HR đang tăng.\n"
        "Yêu cầu:\n"
        "- Trả về JSON hợp lệ duy nhất, không markdown fence, không giải thích ngoài JSON.\n"
        "- title: tiếng Việt có dấu, 3-8 từ, mô tả đúng chủ đề chính, không lấy các từ hỏi như 'như thế nào'.\n"
        "- summary: tiếng Việt có dấu, 1 đoạn ngắn, hữu ích cho nhân viên, chỉ dựa trên nguồn/câu trả lời bên dưới.\n"
        "- Không hiển thị chunk id, không ghi tên section nội bộ, nếu nhắc nguồn thì chỉ nhắc tên tài liệu.\n\n"
        f"CÂU HỎI MẪU:\n{questions}\n\n"
        f"CÂU TRẢ LỜI MẪU:\n{answer_block}\n\n"
        f"NGUỒN:\n{sources}\n\n"
        'JSON schema: {"title":"...","summary":"..."}'
    )


def _parse_trend_json(text: str) -> dict[str, Any] | None:
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", cleaned)
        if not match:
            return None
        try:
            parsed = json.loads(match.group(0))
        except json.JSONDecodeError:
            return None
    return parsed if isinstance(parsed, dict) else None


def _clean_llm_trend_text(text: str) -> str:
    return _strip_internal_chunk_labels(" ".join(text.split())).strip()


def _build_trend_answer_summary(*, title: str, items: list[QueryLog], citations: list[Citation]) -> str:
    topic_name = _display_title(title)
    question_examples = _unique_values(item.query for item in items)[:3]
    answer_examples = _unique_values(item.answer or "" for item in items if item.answer)[:3]

    if citations:
        source = citations[0]
        supported_text = _restore_common_vietnamese_diacritics(_compact_text(source.excerpt, max_len=420))
        summary = (
            f"Tóm tắt câu trả lời cho chủ đề {topic_name}: {supported_text} "
            f"Nguồn tham khảo chính: {source.document_title}."
        )
    elif answer_examples:
        combined_answer = _compact_text(" ".join(answer_examples), max_len=520)
        summary = f"Tóm tắt câu trả lời cho chủ đề {topic_name}: {_restore_common_vietnamese_diacritics(combined_answer)}"
    else:
        summary = (
            f"Chủ đề {topic_name} đang được nhiều nhân viên hỏi. "
            "Chưa có đủ câu trả lời có nguồn để tóm tắt, HR nên bổ sung tài liệu hoặc phản hồi chuẩn."
        )

    if question_examples:
        summary += " Câu hỏi thường gặp: " + "; ".join(question_examples) + "."
    return summary


def _sanitize_trend_candidate(candidate: TrendCandidate) -> TrendCandidate:
    return candidate.model_copy(update={"summary": _strip_internal_chunk_labels(candidate.summary)})


def _sanitize_trend_pin(pin: TrendPin) -> TrendPin:
    return pin.model_copy(update={"summary": _strip_internal_chunk_labels(pin.summary)})


def _strip_internal_chunk_labels(text: str) -> str:
    without_source_suffix = re.sub(r"\s+-\s+chunk-\d+\b", "", text, flags=re.IGNORECASE)
    return re.sub(r"\bchunk-\d+\b", "", without_source_suffix, flags=re.IGNORECASE).replace("  ", " ").strip()


def _restore_common_vietnamese_diacritics(text: str) -> str:
    replacements = {
        "Nhan vien": "Nhân viên",
        "nhan vien": "nhân viên",
        "Chinh sach": "Chính sách",
        "chinh sach": "chính sách",
        "chinh thuc": "chính thức",
        "ngay nghi phep": "ngày nghỉ phép",
        "nghi phep": "nghỉ phép",
        "nghỉ phép nam": "nghỉ phép năm",
        "ngay phep": "ngày phép",
        "ngay nghi": "ngày nghỉ",
        "nam moi nam": "năm mỗi năm",
        "moi nam": "mỗi năm",
        "yeu cau": "yêu cầu",
        "quy dinh": "quy định",
        "truoc it nhat": "trước ít nhất",
        "lam viec": "làm việc",
        "chua su dung": "chưa sử dụng",
        "co the": "có thể",
        "chuyen toi da": "chuyển tối đa",
        "sang nam tiep theo": "sang năm tiếp theo",
        "quan ly truc tiep": "quản lý trực tiếp",
        "duyet lich": "duyệt lịch",
        "ke hoach van hanh": "kế hoạch vận hành",
        "phong ban": "phòng ban",
        "bao hiem": "bảo hiểm",
        "khen thuong": "khen thưởng",
        "tien luong": "tiền lương",
    }
    restored = text
    for source, target in replacements.items():
        restored = re.sub(rf"\b{re.escape(source)}\b", target, restored)
    restored = re.sub(r"\bco\b", "có", restored)
    restored = re.sub(r"\bCo\b", "Có", restored)
    restored = re.sub(r"\b12 ngay\b", "12 ngày", restored)
    restored = re.sub(r"\b3 ngay\b", "3 ngày", restored)
    restored = re.sub(r"\b5 ngay\b", "5 ngày", restored)
    return restored


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
