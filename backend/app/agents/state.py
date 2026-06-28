from __future__ import annotations

from typing import Any, Literal, TypedDict

from app.models.schemas import ChatAction, Citation, Ticket


ChatIntent = Literal["hr_metric", "ticket_create", "policy_question", "general", "blocked"]
RequestedTool = Literal["hris"]


class AgentState(TypedDict, total=False):
    """State schema cho LangGraph agent.

    Mỗi node đọc và ghi vào state này.
    total=False cho phép tất cả fields là optional.
    """

    query: str
    context: str
    current_user: Any
    session_id: str
    message_id: str
    conversation_context: str
    db: Any
    guardrail: Any
    intent: ChatIntent
    requested_tool: RequestedTool
    citations: list[Citation]
    answer: str
    actions: list[ChatAction]
    refusal_reason: str | None
    ticket: Ticket
    analysis: str
    response: str
    error: str
    metadata: dict
    escalated_ticket_id: str | None
