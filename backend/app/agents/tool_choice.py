from __future__ import annotations

import re
import unicodedata
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError

from app.agents.state import AgentState
from app.services import llm
from app.services.guardrails import looks_like_hr_question
from app.services.hris import should_call_hris_tool

ToolName = Literal["get_hr_metrics", "search_policy", "request_ticket_escalation", "answer_general"]
ToolChoiceSource = Literal["model", "fallback_rule"]


class ToolChoice(BaseModel):
    tool_name: ToolName
    arguments: dict[str, Any] = Field(default_factory=dict)
    source: ToolChoiceSource
    fallback_reason: str | None = None


async def choose_tool_for_state(state: AgentState) -> ToolChoice:
    query = state.get("query", "")
    conversation_context = state.get("conversation_context", "")
    model_choice = _validated_model_choice(
        llm.choose_chat_tool_with_gemini(
            query,
            conversation_context=conversation_context,
        )
    )
    if model_choice is not None:
        return model_choice
    return fallback_tool_choice(query, conversation_context, fallback_reason="model_unavailable_or_invalid")


def tool_choice_to_state(choice: ToolChoice) -> dict:
    metadata = {
        "tool_choice_source": choice.source,
        "tool_choice_name": choice.tool_name,
    }
    if choice.fallback_reason:
        metadata["tool_choice_fallback_reason"] = choice.fallback_reason

    if choice.tool_name == "get_hr_metrics":
        return {"intent": "hr_metric", "requested_tool": "hris", "metadata": metadata}
    if choice.tool_name == "search_policy":
        return {"intent": "policy_question", "metadata": metadata}
    if choice.tool_name == "request_ticket_escalation":
        return {"intent": "ticket_create", "metadata": metadata}
    return {"intent": "general", "metadata": metadata}


def fallback_tool_choice(
    query: str,
    conversation_context: str = "",
    *,
    fallback_reason: str | None = None,
) -> ToolChoice:
    if _is_ticket_detail_followup(conversation_context, query) or _is_ticket_intent(query):
        return ToolChoice(
            tool_name="request_ticket_escalation",
            arguments={"message": query, "reason": "user_requested", "priority": "normal"},
            source="fallback_rule",
            fallback_reason=fallback_reason,
        )
    if should_call_hris_tool(query):
        return ToolChoice(
            tool_name="get_hr_metrics",
            arguments={"query": query},
            source="fallback_rule",
            fallback_reason=fallback_reason,
        )
    if looks_like_hr_question(query):
        return ToolChoice(
            tool_name="search_policy",
            arguments={"query": query},
            source="fallback_rule",
            fallback_reason=fallback_reason,
        )
    return ToolChoice(
        tool_name="answer_general",
        arguments={"query": query},
        source="fallback_rule",
        fallback_reason=fallback_reason,
    )


def _validated_model_choice(raw_choice: dict[str, Any] | None) -> ToolChoice | None:
    if not raw_choice:
        return None
    try:
        return ToolChoice(
            tool_name=raw_choice.get("name"),
            arguments=_normalized_arguments(raw_choice.get("args")),
            source="model",
        )
    except ValidationError:
        return None


def _normalized_arguments(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {}


def _is_ticket_intent(message: str) -> bool:
    normalized = _normalize(message)
    return bool(
        re.search(r"\b(tao|mo|gui|lap)\s+(ticket|phieu|yeu\s+cau)\b", normalized)
        or re.search(r"\b(ticket|phieu\s+ho\s+tro|yeu\s+cau\s+ho\s+tro)\b", normalized)
    )


def _is_ticket_detail_followup(conversation_context: str, query: str = "") -> bool:
    raw = conversation_context.lower()
    if "ticket" in raw and "noi dung" in raw:
        return True
    normalized = _normalize(conversation_context)
    pending_markers = [
        "noi dung can hr ho tro",
        "cho minh biet noi dung can hr ho tro",
        "cho minh biet noi dung can nhan su ho tro",
        "cung cap them thong tin de minh tao ticket",
        "minh tao ticket nhe",
    ]
    has_pending_prompt = any(marker in normalized for marker in pending_markers) or (
        "noi dung" in normalized and "ticket" in normalized
    )
    has_recent_ticket_request = "ticket" in normalized and any(
        phrase in normalized for phrase in {"tao ticket", "t o ticket"}
    )
    return has_pending_prompt or (has_recent_ticket_request and _has_ticket_description(query))


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


def _normalize(message: str) -> str:
    normalized = unicodedata.normalize("NFKD", message.lower().replace("\u0111", "d").replace("\u0110", "D"))
    ascii_text = "".join(char for char in normalized if not unicodedata.combining(char))
    ascii_text = re.sub(r"[^a-z0-9\s]", " ", ascii_text)
    return re.sub(r"\s+", " ", ascii_text).strip()
