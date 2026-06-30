from __future__ import annotations

import re
import unicodedata

from app.agents.state import AgentState
from app.agents.tool_choice import choose_tool_for_state, tool_choice_to_state
from app.agents.tools.example_tool import get_hr_metrics_tool, search_policy_tool
from app.models.schemas import ChatAction, ChatResponse
from app.services.guardrails import evaluate_chat_guardrails, looks_like_hr_question
from app.services.llm import build_cited_answer, build_general_answer, build_refusal_answer
from app.services.retrieval import user_has_readable_chunks


async def guardrail_node(state: AgentState) -> dict:
    query = state.get("query", "")
    guardrail = evaluate_chat_guardrails(query)
    if guardrail.allowed or guardrail.refusal_reason is None:
        return {"guardrail": guardrail}

    actions = [ChatAction(type="none", label="Không cần thao tác", data=None)]
    answer = build_refusal_answer(guardrail.refusal_reason)
    if guardrail.refusal_reason == "outside_scope":
        actions = [_escalation_action(query, guardrail.refusal_reason, state.get("session_id"))]
        answer = f"{answer}\n\nBạn có muốn gửi ticket cho HR để được hỗ trợ tiếp không?"

    return {
        "guardrail": guardrail,
        "intent": "blocked",
        "answer": answer,
        "actions": actions,
        "citations": [],
        "refusal_reason": guardrail.refusal_reason,
        "escalated_ticket_id": None,
    }


async def classify_intent_node(state: AgentState) -> dict:
    return tool_choice_to_state(await choose_tool_for_state(state))


async def hr_metrics_node(state: AgentState) -> dict:
    if state.get("requested_tool") != "hris":
        return await general_answer_node(state)

    user = state.get("current_user")
    metrics = get_hr_metrics_tool(user)
    return {
        "answer": (
            f"Số ngày phép còn lại của bạn là {metrics.leave_days_remaining}. "
            f"Trạng thái bảo hiểm: {_display_label(metrics.insurance_status)}. "
            f"Xét duyệt khen thưởng: {_display_label(metrics.reward_review_status)}."
        ),
        "actions": [
            ChatAction(
                type="hr_metric_lookup",
                label="Số liệu nhân sự cá nhân",
                data=metrics.model_dump(),
            )
        ],
        "citations": [],
        "refusal_reason": None,
        "escalated_ticket_id": None,
    }


async def retrieve_policy_node(state: AgentState) -> dict:
    user = state.get("current_user")
    if user is None:
        return {"citations": [], "metadata": {"has_readable_chunks": False}}
    citations = search_policy_tool(state.get("query", ""), user)
    return {
        "citations": citations,
        "metadata": {
            **state.get("metadata", {}),
            "has_readable_chunks": user_has_readable_chunks(user),
        },
    }


async def answer_with_sources_node(state: AgentState) -> dict:
    citations = state.get("citations", [])
    answer = build_cited_answer(
        state.get("query", ""),
        citations,
        conversation_context=state.get("conversation_context", ""),
    )
    return {
        "answer": answer,
        "actions": [ChatAction(type="none", label="Không cần thao tác", data=None)],
        "refusal_reason": None,
        "escalated_ticket_id": None,
    }


async def handle_no_source_node(state: AgentState) -> dict:
    query = state.get("query", "")
    return {
        "answer": f"{build_refusal_answer('no_source')}\n\nBạn có muốn gửi ticket cho HR để được hỗ trợ tiếp không?",
        "actions": [_escalation_action(query, "no_source", state.get("session_id"))],
        "citations": [],
        "refusal_reason": "no_source",
        "escalated_ticket_id": None,
    }


async def handle_ticket_intent_node(state: AgentState) -> dict:
    query = state.get("query", "")
    if not _has_ticket_description(query):
        return {
            "answer": "Bạn cho mình biết nội dung cần HR hỗ trợ để mình tạo ticket nhé.",
            "actions": [ChatAction(type="none", label="Không cần thao tác", data=None)],
            "citations": [],
            "refusal_reason": None,
            "escalated_ticket_id": None,
        }

    return {
        "answer": "Mình đã ghi nhận nội dung cần HR hỗ trợ. Bạn xác nhận gửi ticket cho HR nhé?",
        "actions": [_escalation_action(query, "user_requested", state.get("session_id"))],
        "citations": [],
        "refusal_reason": None,
        "escalated_ticket_id": None,
    }


async def general_answer_node(state: AgentState) -> dict:
    user = state.get("current_user")
    user_name = getattr(user, "full_name", "bạn")
    answer = build_general_answer(
        state.get("query", ""),
        user_name,
        conversation_context=state.get("conversation_context", ""),
    )
    return {
        "answer": answer,
        "actions": [ChatAction(type="none", label="Không cần thao tác", data=None)],
        "citations": [],
        "refusal_reason": None,
        "escalated_ticket_id": None,
    }


async def finalize_response_node(state: AgentState) -> dict:
    response = ChatResponse(
        message_id=state.get("message_id", "msg-agent"),
        session_id=state.get("session_id", "session-agent"),
        answer=state.get("answer", ""),
        citations=state.get("citations", []),
        actions=state.get("actions", [ChatAction(type="none", label="Không cần thao tác", data=None)]),
        escalated_ticket_id=state.get("escalated_ticket_id"),
        refusal_reason=state.get("refusal_reason"),
    )
    return {"response": response}


async def analyze_node(state: AgentState) -> dict:
    """Compatibility node kept for older direct tests/imports."""
    return await classify_intent_node(state)


async def respond_node(state: AgentState) -> dict:
    """Compatibility node kept for older direct tests/imports."""
    return await general_answer_node(state)


def is_blocked(state: AgentState) -> bool:
    return state.get("intent") == "blocked"


def route_intent(state: AgentState) -> str:
    return state.get("intent", "general")


def route_retrieval(state: AgentState) -> str:
    if state.get("citations"):
        return "answer_with_sources"
    if state.get("metadata", {}).get("has_readable_chunks") and looks_like_hr_question(state.get("query", "")):
        return "handle_no_source"
    return "general_answer"


def _escalation_action(query: str, reason: str, session_id: str | None) -> ChatAction:
    return ChatAction(
        type="escalation_confirmation_required",
        label="Cần xác nhận gửi ticket cho HR",
        data={
            "message": query,
            "reason": reason,
            "priority": "normal",
            "session_id": session_id,
        },
    )


def _is_ticket_intent(message: str) -> bool:
    normalized = _normalize(message)
    return bool(
        re.search(r"\b(tao|mo|gui|lap)\s+(ticket|phieu|yeu\s+cau)\b", normalized)
        or re.search(r"\b(ticket|phieu\s+ho\s+tro|yeu\s+cau\s+ho\s+tro)\b", normalized)
    )


def _has_ticket_description(message: str) -> bool:
    normalized = _normalize(message)
    removable_patterns = [
        r"\b(toi|minh|em|anh|chi|ban)\b",
        r"\b(muon|can|hay|vui\s+long|giup|giup\s+toi|cho\s+toi)\b",
        r"\b(tao|mo|gui|lap)\b",
        r"\b(ticket|phieu|yeu\s+cau|ho\s+tro|hr|nhan\s+su)\b",
        r"\b(ve|cho|den|toi|voi)\b",
    ]
    remaining = normalized
    for pattern in removable_patterns:
        remaining = re.sub(pattern, " ", remaining)
    meaningful_tokens = re.findall(r"[a-z0-9]{2,}", remaining)
    return len(meaningful_tokens) >= 3


def _is_ticket_detail_followup(conversation_context: str, query: str = "") -> bool:
    raw = conversation_context.lower()
    if "ticket" in raw and ("nội dung" in raw or "noi dung" in raw):
        return True
    normalized = _normalize(conversation_context)
    pending_markers = [
        "noi dung can hr ho tro",
        "cho minh biet noi dung can hr ho tro",
        "cho minh biet noi dung can nhan su ho tro",
        "cung cap them thong tin de minh tao ticket",
        "minh tao ticket nhe",
    ]
    has_pending_prompt = any(marker in normalized for marker in pending_markers) or ("noi dung" in normalized and "ticket" in normalized)
    has_recent_ticket_request = "ticket" in normalized and any(phrase in normalized for phrase in {"tao ticket", "t o ticket"})
    return has_pending_prompt or (has_recent_ticket_request and _has_ticket_description(query))


def _normalize(message: str) -> str:
    normalized = unicodedata.normalize("NFKD", message.lower().replace("đ", "d").replace("Đ", "D"))
    ascii_text = "".join(char for char in normalized if not unicodedata.combining(char))
    ascii_text = re.sub(r"[^a-z0-9\s]", " ", ascii_text)
    return re.sub(r"\s+", " ", ascii_text).strip()


def _display_label(value: str) -> str:
    labels = {
        "active": "Đang hiệu lực",
        "approved": "Đã duyệt",
        "in_review": "Đang xét",
        "inactive": "Không hiệu lực",
        "not_started": "Chưa bắt đầu",
        "pending": "Đang chờ",
        "rejected": "Từ chối",
    }
    return labels.get(value, value)
