from __future__ import annotations

import re
import unicodedata

from app.agents.state import AgentState
from app.agents.ticket_draft_agent import (
    TICKET_CATEGORY_LABELS,
    format_ticket_message,
    rewrite_ticket_description,
    run_ticket_draft_agent,
    suggest_ticket_details,
)
from app.agents.tool_choice import choose_tool_for_state, tool_choice_to_state
from app.agents.tools.example_tool import get_hr_metrics_tool, search_policy_tool
from app.config import get_settings
from app.guardrails.config import guardrails_enabled
from app.guardrails.messages import AMBIGUOUS_MESSAGE, SENSITIVE_DATA_MESSAGE
from app.models.schemas import ChatAction, ChatResponse, ChatWorkflowState, PendingTicketDraft
from app.services.chat_session_state import (
    clear_chat_session_state,
    default_ticket_draft_state,
    preserve_conversation_memory,
    save_chat_session_state,
)
from app.services.guardrails import (
    check_input_safeguard,
    check_output_safeguard,
    check_tool_guardrail,
    check_topic_scope,
    evaluate_chat_guardrails,
    looks_like_hr_question,
)
from app.services.llm import build_cited_answer, build_general_answer, build_refusal_answer
from app.services.retrieval import user_has_readable_chunks

TICKET_PAUSE_REMINDER = "Ticket đang được tạm giữ. Khi muốn tiếp tục, bạn có thể nói 'tiếp tục tạo ticket'."


async def input_safeguard_node(state: AgentState) -> dict:
    query = state.get("query", "")
    decision = await check_input_safeguard(query, user_context=_user_context(state.get("current_user")))
    if _active_flow(state) == "ticket_draft" and (decision.blocked or not decision.allowed):
        local_guardrail = evaluate_chat_guardrails(query)
        if local_guardrail.allowed:
            decision = decision.model_copy(
                update={
                    "allowed": True,
                    "blocked": False,
                    "requires_handoff": False,
                    "action": "allow",
                    "user_message": "",
                    "internal_reason": "active_ticket_draft_rule_allow",
                    "reason_code": "allow",
                }
            )
    if decision.allowed and not decision.blocked:
        return {
            "input_safeguard": decision.model_dump(),
            "guardrail": evaluate_chat_guardrails(query),
        }

    return _blocked_guardrail_state(
        state,
        stage="input",
        user_message=decision.user_message,
        refusal_reason=_refusal_from_reason_code(decision.reason_code),
        input_safeguard=decision.model_dump(),
    )


async def topic_scope_node(state: AgentState) -> dict:
    if not guardrails_enabled():
        return {}

    query = state.get("query", "")
    metadata = dict(state.get("metadata", {}))
    if _active_flow(state) == "ticket_draft":
        metadata.update(
            {
                "ticket_flow_action": "pause",
                "should_update_ticket_context": False,
                "active_ticket_paused": True,
            }
        )

    if _is_bare_numeric_reply_without_pending_choice(query, state.get("conversation_context", "")):
        return _clarification_state(
            state,
            stage="topic",
            user_message=_bare_numeric_choice_message(),
            reason_code="bare_numeric_reply",
        )

    decision = await check_topic_scope(query)
    result = {"topic_scope": decision.model_dump(), "metadata": metadata}

    if decision.scope == "out_of_scope":
        result.update(
            _blocked_guardrail_state(
                state,
                stage="topic",
                user_message=decision.user_message,
                refusal_reason="outside_scope",
                topic_scope=decision.model_dump(),
            )
        )
        return result

    if decision.scope == "ambiguous" or decision.confidence < get_settings().topic_classifier_confidence_threshold:
        result.update(
            _blocked_guardrail_state(
                state,
                stage="topic",
                user_message=decision.user_message or AMBIGUOUS_MESSAGE,
                refusal_reason="low_confidence",
                topic_scope=decision.model_dump(),
            )
        )
        return result

    if (
        decision.sensitivity == "confidential"
        and not _is_workplace_complaint_topic(decision.topic)
        and not _user_can_access_confidential_hr(state.get("current_user"))
    ):
        result.update(
            _blocked_guardrail_state(
                state,
                stage="topic",
                user_message=decision.user_message or SENSITIVE_DATA_MESSAGE,
                refusal_reason="sensitive",
                topic_scope=decision.model_dump(),
            )
        )
    return result


async def output_safeguard_node(state: AgentState) -> dict:
    if state.get("guardrail_blocked"):
        answer = _append_ticket_pause_reminder_if_needed(state, state.get("answer", ""))
        return {
            "answer": answer,
            "output_safeguard": {
                "allowed": True,
                "action": "allow",
                "risk_level": "none",
                "user_message": "",
                "redacted_text": answer,
                "internal_reason": "prevalidated_guardrail_response",
            }
        }

    original_answer = state.get("answer", "")
    answer = _append_ticket_pause_reminder_if_needed(state, original_answer)
    citations = state.get("citations", [])
    topic_scope = state.get("topic_scope") or {}
    actions = state.get("actions", [])
    decision = await check_output_safeguard(
        answer,
        user_message=state.get("query", ""),
        context_summary=_output_context_summary(state, citations),
        has_citations=bool(citations),
        has_tool_result=any(
            _action_type(action)
            in {"hr_metric_lookup", "ticket_draft_confirmation", "escalation_confirmation_required"}
            for action in actions
        ),
        topic=str(topic_scope.get("topic", "")),
    )
    answer_update = {"answer": answer} if answer != original_answer else {}
    if decision.action == "allow":
        return {"output_safeguard": decision.model_dump(), **answer_update}
    if decision.action == "redact":
        return {"output_safeguard": decision.model_dump(), "answer": decision.redacted_text or decision.user_message}
    fallback_answer = _append_ticket_pause_reminder_if_needed(state, decision.user_message)
    return {
        "output_safeguard": decision.model_dump(),
        "answer": fallback_answer,
        "citations": [],
        "actions": [ChatAction(type="none", label="KhÃ´ng cáº§n thao tÃ¡c", data=None)],
        "refusal_reason": state.get("refusal_reason") or "guardrail_output",
    }


async def guardrail_node(state: AgentState) -> dict:
    if guardrails_enabled():
        return await input_safeguard_node(state)

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
    if (state.get("metadata") or {}).get("active_ticket_paused"):
        state = {**state, "conversation_context": ""}
    result = tool_choice_to_state(await choose_tool_for_state(state))
    if state.get("metadata"):
        result["metadata"] = {**state.get("metadata", {}), **result.get("metadata", {})}
    return result


async def hr_metrics_node(state: AgentState) -> dict:
    if state.get("requested_tool") != "hris":
        return await general_answer_node(state)

    user = state.get("current_user")
    tool_decision = await check_tool_guardrail("get_hr_metrics", user, side_effect=False)
    if not tool_decision.allowed:
        return _tool_blocked_state(tool_decision)

    metrics = get_hr_metrics_tool(user)
    return {
        "answer": _format_hr_metrics_answer(state.get("query", ""), metrics),
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
    session_id = state.get("session_id")
    if _is_cancel_ticket_draft_message(query) and _active_flow(state) == "ticket_draft":
        if session_id and state.get("db") is not None:
            await clear_chat_session_state(state.get("db"), session_id)
        return {
            "answer": "Mình đã hủy nháp ticket này.",
            "actions": [ChatAction(type="none", label="Không cần thao tác", data=None)],
            "citations": [],
            "refusal_reason": None,
            "escalated_ticket_id": None,
            "session_state": preserve_conversation_memory(
                ChatWorkflowState(),
                state.get("session_state"),
            ).model_dump(mode="json"),
        }

    tool_decision = await check_tool_guardrail("create_hr_ticket", state.get("current_user"), side_effect=True)
    if not tool_decision.allowed and tool_decision.action != "require_confirmation":
        return _tool_blocked_state(tool_decision)

    pending_draft = _pending_ticket_draft_from_state(state)
    if _active_flow(state) == "ticket_draft" and pending_draft is not None and _has_complete_ticket_draft(pending_draft):
        normalized_query = _normalize(query)
        if _is_ticket_draft_guidance_question(normalized_query):
            draft = _with_ticket_suggestions(pending_draft)
            ticket_context = _ticket_context_from_state(state)
            next_state = await _save_ticket_draft_state(state, draft, ticket_context)
            return {
                "answer": _ticket_draft_guidance_answer(draft),
                "actions": [_ticket_draft_action(draft, state.get("session_id"))],
                "citations": [],
                "refusal_reason": None,
                "escalated_ticket_id": None,
                "session_state": next_state.model_dump(mode="json"),
            }
        if _is_ticket_submit_confirmation_message(normalized_query):
            draft = _with_ticket_suggestions(pending_draft)
            return {
                "answer": "Mình đang giữ nháp ticket bên dưới. Bạn kiểm tra lại rồi bấm Gửi yêu cầu để tạo ticket nhé.",
                "actions": [_ticket_draft_action(draft, state.get("session_id"))],
                "citations": [],
                "refusal_reason": None,
                "escalated_ticket_id": None,
            }
        if _is_ticket_suggestion_prompt_only(query, _with_ticket_suggestions(pending_draft).suggested_fields):
            draft = _with_ticket_suggestions(pending_draft)
            return {
                "answer": _ticket_draft_need_detail_answer(draft),
                "actions": [_ticket_draft_action(draft, state.get("session_id"))],
                "citations": [],
                "refusal_reason": None,
                "escalated_ticket_id": None,
            }
        if _is_ticket_draft_detail_update(normalized_query):
            draft = _merge_ticket_draft_detail(pending_draft, query)
            updated_ticket_context = _append_ticket_context(_ticket_context_from_state(state), "Người dùng", query)
            next_state = await _save_ticket_draft_state(state, draft, updated_ticket_context)
            return {
                "answer": _ticket_draft_updated_answer(draft),
                "actions": [_ticket_draft_action(draft, state.get("session_id"))],
                "citations": [],
                "refusal_reason": None,
                "escalated_ticket_id": None,
                "session_state": next_state.model_dump(mode="json"),
            }

    ticket_context = _ticket_context_from_state(state)
    draft = run_ticket_draft_agent(query, ticket_context)
    updated_ticket_context = _append_ticket_context(ticket_context, "Người dùng", query)
    if not draft.ready or not draft.title or not draft.category or not draft.description:
        next_state = default_ticket_draft_state(session_id or "", state.get("session_state"))
        if draft.missing_fields:
            next_state.pending_ticket_draft.missing_fields = draft.missing_fields
        if draft.suggested_fields:
            next_state.pending_ticket_draft.suggested_fields = draft.suggested_fields
        answer = draft.question or "Bạn cho mình biết nội dung cần HR hỗ trợ để mình tạo ticket nhé."
        next_state = next_state.model_copy(
            update={"ticket_context": _append_ticket_context(updated_ticket_context, "AI", answer)}
        )
        if session_id and state.get("db") is not None:
            await save_chat_session_state(state.get("db"), session_id, next_state)
        return {
            "answer": answer,
            "actions": [ChatAction(type="none", label="Không cần thao tác", data=None)],
            "citations": [],
            "refusal_reason": None,
            "escalated_ticket_id": None,
            "session_state": next_state.model_dump(mode="json"),
        }

    next_state = preserve_conversation_memory(
        ChatWorkflowState(
            active_flow="ticket_draft",
            pending_ticket_draft=PendingTicketDraft(
                title=draft.title,
                category=draft.category,
                description=draft.description,
                priority=draft.priority,
                missing_fields=[],
                suggested_fields=draft.suggested_fields or suggest_ticket_details(draft.category, draft.description),
                session_id=session_id,
            ),
            last_intent="ticket_create",
            ticket_context=updated_ticket_context,
        ),
        state.get("session_state"),
    )
    if session_id and state.get("db") is not None:
        await save_chat_session_state(state.get("db"), session_id, next_state)
    return {
        "answer": _ticket_draft_ready_answer(draft.title, draft.description, draft.suggested_fields),
        "actions": [
            ChatAction(
                type="ticket_draft_confirmation",
                label="Xác nhận yêu cầu hỗ trợ (AI đã điền sẵn)",
                data={
                    "title": draft.title,
                    "category": draft.category,
                    "category_label": TICKET_CATEGORY_LABELS[draft.category],
                    "description": draft.description,
                    "message": format_ticket_message(draft.title, draft.category, draft.description),
                    "reason": "user_requested",
                    "priority": draft.priority,
                    "session_id": state.get("session_id"),
                    "suggested_fields": draft.suggested_fields or suggest_ticket_details(draft.category, draft.description),
                },
            )
        ],
        "citations": [],
        "refusal_reason": None,
        "escalated_ticket_id": None,
        "session_state": next_state.model_dump(mode="json"),
    }


async def general_answer_node(state: AgentState) -> dict:
    if _is_bare_numeric_reply_without_pending_choice(state.get("query", ""), state.get("conversation_context", "")):
        return {
            "answer": (
                "Mình chưa thấy danh sách lựa chọn nào đang chờ chọn bằng số. "
                "Bạn vui lòng nhập rõ câu hỏi HR, ví dụ: chính sách nghỉ phép, bảo hiểm, phúc lợi, hợp đồng hoặc tạo ticket cho HR."
            ),
            "actions": [ChatAction(type="none", label="KhÃ´ng cáº§n thao tÃ¡c", data=None)],
            "citations": [],
            "refusal_reason": None,
            "escalated_ticket_id": None,
        }

    if (state.get("topic_scope") or {}).get("topic") == "hr_helpdesk_usage":
        return {
            "answer": (
                "Mình có thể hỗ trợ các câu hỏi liên quan đến nhân sự, chính sách công ty, "
                "quyền lợi, nghỉ phép, lương thưởng, hợp đồng, onboarding/offboarding, "
                "quy trình HR nội bộ và cách sử dụng HR helpdesk."
            ),
            "actions": [ChatAction(type="none", label="KhÃ´ng cáº§n thao tÃ¡c", data=None)],
            "citations": [],
            "refusal_reason": None,
            "escalated_ticket_id": None,
        }

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
    return state.get("intent") == "blocked" or bool(state.get("guardrail_blocked"))


def should_continue_active_ticket_flow(state: AgentState) -> bool:
    if _active_flow(state) != "ticket_draft":
        return False
    query = state.get("query", "")
    normalized = _normalize(query)
    if not normalized:
        return True
    if (
        _is_cancel_ticket_draft_message(query)
        or _is_ticket_submit_confirmation_message(normalized)
        or _is_continue_ticket_message(normalized)
        or _is_ticket_intent(query)
    ):
        return True
    if _looks_like_policy_or_general_question(normalized):
        return False
    return True


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


def _blocked_guardrail_state(
    state: AgentState,
    *,
    stage: str,
    user_message: str,
    refusal_reason: str,
    **decision_payload: dict,
) -> dict:
    return {
        **decision_payload,
        "guardrail_blocked": True,
        "guardrail_user_message": user_message,
        "intent": "blocked",
        "answer": user_message,
        "actions": [ChatAction(type="none", label="KhÃ´ng cáº§n thao tÃ¡c", data=None)],
        "citations": [],
        "refusal_reason": refusal_reason,
        "escalated_ticket_id": None,
        "metadata": {**state.get("metadata", {}), "guardrail_block_stage": stage},
    }


def _clarification_state(state: AgentState, *, stage: str, user_message: str, reason_code: str) -> dict:
    return {
        "guardrail_blocked": True,
        "guardrail_user_message": user_message,
        "intent": "blocked",
        "answer": user_message,
        "actions": [ChatAction(type="none", label="KhÃƒÂ´ng cÃ¡ÂºÂ§n thao tÃƒÂ¡c", data=None)],
        "citations": [],
        "refusal_reason": None,
        "escalated_ticket_id": None,
        "metadata": {**state.get("metadata", {}), "guardrail_block_stage": stage, "reason_code": reason_code},
    }


def _tool_blocked_state(tool_decision) -> dict:
    return {
        "tool_guardrails": [tool_decision.model_dump()],
        "guardrail_blocked": True,
        "intent": "blocked",
        "answer": tool_decision.user_message,
        "actions": [ChatAction(type="none", label="KhÃ´ng cáº§n thao tÃ¡c", data=None)],
        "citations": [],
        "refusal_reason": "sensitive" if tool_decision.action in {"block", "handoff"} else "require_auth",
        "escalated_ticket_id": None,
    }


def _refusal_from_reason_code(reason_code: str) -> str:
    if reason_code in {"jailbreak", "outside_scope", "sensitive"}:
        return reason_code
    return "guardrail_input"


def _user_context(user) -> dict | None:
    if user is None:
        return None
    return {
        "id": str(getattr(user, "id", "")),
        "role": getattr(user, "role", ""),
        "department_id": getattr(user, "department_id", None),
    }


def _user_can_access_confidential_hr(user) -> bool:
    return getattr(user, "role", "") in {"hr_admin", "admin"}


def _is_workplace_complaint_topic(topic: str) -> bool:
    return topic in {
        "workplace_harassment_complaint",
        "workplace_misconduct",
        "discrimination_complaint",
        "bullying_complaint",
        "retaliation_complaint",
    }


def _active_flow(state: AgentState) -> str:
    session_state = state.get("session_state") or {}
    if isinstance(session_state, ChatWorkflowState):
        return session_state.active_flow
    if isinstance(session_state, dict):
        return str(session_state.get("active_flow") or "none")
    return "none"


def _action_type(action) -> str | None:
    if isinstance(action, dict):
        return action.get("type")
    return getattr(action, "type", None)


def _pending_ticket_draft_from_state(state: AgentState) -> PendingTicketDraft | None:
    session_state = state.get("session_state") or {}
    if isinstance(session_state, ChatWorkflowState):
        return session_state.pending_ticket_draft
    if isinstance(session_state, dict):
        raw_draft = session_state.get("pending_ticket_draft")
        if isinstance(raw_draft, PendingTicketDraft):
            return raw_draft
        if isinstance(raw_draft, dict):
            try:
                return PendingTicketDraft.model_validate(raw_draft)
            except Exception:
                return None
    return None


def _has_complete_ticket_draft(draft: PendingTicketDraft) -> bool:
    return bool(draft.title and draft.category and draft.description)


def _with_ticket_suggestions(draft: PendingTicketDraft) -> PendingTicketDraft:
    if draft.suggested_fields:
        return draft
    return draft.model_copy(
        update={"suggested_fields": suggest_ticket_details(draft.category, draft.description or "")}
    )


def _ticket_draft_state(state: AgentState, draft: PendingTicketDraft, ticket_context: str) -> ChatWorkflowState:
    return preserve_conversation_memory(
        ChatWorkflowState(
            active_flow="ticket_draft",
            pending_ticket_draft=_with_ticket_suggestions(draft),
            last_intent="ticket_create",
            ticket_context=ticket_context,
        ),
        state.get("session_state"),
    )


async def _save_ticket_draft_state(
    state: AgentState,
    draft: PendingTicketDraft,
    ticket_context: str,
) -> ChatWorkflowState:
    next_state = _ticket_draft_state(state, draft, ticket_context)
    session_id = state.get("session_id")
    if session_id and state.get("db") is not None:
        await save_chat_session_state(state.get("db"), session_id, next_state)
    return next_state


def _ticket_draft_action(draft: PendingTicketDraft, session_id: str | None) -> ChatAction:
    draft = _with_ticket_suggestions(draft)
    category = draft.category or "other"
    title = draft.title or "Yêu cầu hỗ trợ HR"
    description = draft.description or ""
    return ChatAction(
        type="ticket_draft_confirmation",
        label="Xác nhận yêu cầu hỗ trợ (AI đã điền sẵn)",
        data={
            "title": title,
            "category": category,
            "category_label": TICKET_CATEGORY_LABELS[category],
            "description": description,
            "message": format_ticket_message(title, category, description),
            "reason": "user_requested",
            "priority": draft.priority,
            "session_id": session_id or draft.session_id,
            "suggested_fields": draft.suggested_fields,
        },
    )


def _merge_ticket_draft_detail(draft: PendingTicketDraft, query: str) -> PendingTicketDraft:
    draft = _with_ticket_suggestions(draft)
    detail = _clean_ticket_detail_update(query, draft.suggested_fields)
    description = rewrite_ticket_description(draft.description or "", detail, draft.category)
    return draft.model_copy(
        update={
            "description": description,
            "suggested_fields": suggest_ticket_details(draft.category, description),
        }
    )


def _clean_ticket_detail_update(query: str, suggested_fields: list[str] | None = None) -> str:
    cleaned = re.sub(
        r"^\s*(bo\s+sung|bổ\s+sung|them|thêm|cap\s+nhat|cập\s+nhật|mo\s+ta|mô\s+tả)\s*[:\-]?\s*",
        "",
        str(query or "").strip(),
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(r"^\s*(la|là)\s+", "", cleaned, flags=re.IGNORECASE)
    cleaned = _strip_suggestion_label(cleaned, suggested_fields or [])
    return " ".join(cleaned.split())


def _strip_suggestion_label(text: str, suggested_fields: list[str]) -> str:
    if ":" not in text:
        return text
    label, value = text.split(":", 1)
    normalized_label = _normalize(label)
    for suggestion in suggested_fields:
        normalized_suggestion = _normalize(suggestion)
        if normalized_label == normalized_suggestion or normalized_label.endswith(normalized_suggestion):
            return value.strip()
    return text


def _is_ticket_suggestion_prompt_only(query: str, suggested_fields: list[str]) -> bool:
    if not suggested_fields:
        return False
    normalized_query = _normalize(str(query or "").strip().rstrip(":"))
    for suggestion in suggested_fields:
        normalized_suggestion = _normalize(suggestion)
        if normalized_query in {normalized_suggestion, f"bo sung {normalized_suggestion}"}:
            return True
    return _clean_ticket_detail_update(query, suggested_fields) == ""


def _append_ticket_description(current: str, detail: str) -> str:
    current = str(current or "").strip()
    detail = str(detail or "").strip()
    if not detail:
        return current
    if _normalize(detail) in _normalize(current):
        return current
    if not current:
        return detail
    return f"{current}\n\nThông tin bổ sung: {detail}"


def _ticket_context_from_state(state: AgentState) -> str:
    session_state = state.get("session_state") or {}
    if isinstance(session_state, ChatWorkflowState):
        return session_state.ticket_context
    if isinstance(session_state, dict):
        return str(session_state.get("ticket_context") or "")
    return ""


def _append_ticket_context(context: str, role: str, message: str) -> str:
    compact_message = " ".join(str(message or "").split())
    if not compact_message:
        return context
    updated = "\n".join(part for part in [context.strip(), f"{role}: {compact_message}"] if part)
    return updated[-4000:]


def _append_ticket_pause_reminder_if_needed(state: AgentState, answer: str) -> str:
    metadata = state.get("metadata") or {}
    active_ticket_paused = metadata.get("active_ticket_paused") or (
        _active_flow(state) == "ticket_draft" and not _has_action_type(state.get("actions", []), "ticket_draft_confirmation")
    )
    if not active_ticket_paused:
        return answer
    text = str(answer or "").rstrip()
    if not text or TICKET_PAUSE_REMINDER in text:
        return text
    return f"{text}\n\n{TICKET_PAUSE_REMINDER}"


def _has_action_type(actions, action_type: str) -> bool:
    return any(_action_type(action) == action_type for action in actions or [])


def _is_cancel_ticket_draft_message(message: str) -> bool:
    normalized = _normalize(message)
    return bool(
        re.fullmatch(r"(huy|thoi|cancel)", normalized)
        or re.search(r"\b(khong\s+tao\s+nua|huy\s+ticket|huy\s+nhap|huy\s+draft|cancel\s+ticket)\b", normalized)
    )


def _is_continue_ticket_message(normalized: str) -> bool:
    return bool(
        re.fullmatch(r"(tiep\s+tuc|continue|resume)", normalized)
        or re.search(r"\b(tiep\s+tuc\s+(tao\s+)?ticket|quay\s+lai\s+ticket|resume\s+ticket)\b", normalized)
    )


def _is_ticket_submit_confirmation_message(normalized: str) -> bool:
    return bool(
        re.fullmatch(r"(dong\s+y|xac\s+nhan|ok|okay|yes|submit)", normalized)
        or re.search(r"\b(dong\s+y\s+gui\s+ticket|xac\s+nhan\s+gui\s+ticket|gui\s+ticket|submit\s+ticket|ok\s+tao\s+ticket)\b", normalized)
    )


def _looks_like_policy_or_general_question(normalized: str) -> bool:
    if normalized in {"hello", "hi", "hey", "xin chao", "chao ban", "ban la ai"}:
        return True
    if re.search(r"\b(viet|tao|debug|sua|giai|huong\s+dan|lam)\b.{0,80}\b(code|script|python|javascript|fastapi|sql|thuat\s+toan|quicksort)\b", normalized):
        return True
    return bool(
        re.search(
            r"\b(chinh\s+sach|quy\s+dinh|quy\s+trinh|thu\s+tuc|la\s+gi|nhu\s+the\s+nao|bao\s+nhieu|duoc\s+khong|co\s+duoc|can\s+bao\s+truoc|muc\s+dong|ban\s+co\s+the|ban\s+la\s+ai)\b",
            normalized,
        )
    )


def _is_ticket_draft_guidance_question(normalized: str) -> bool:
    return bool(
        re.search(r"\b(nen|can|phai)\s+(dien|ghi|mo\s+ta|bo\s+sung)\b", normalized)
        or re.search(r"\b(goi\s+y|huong\s+dan|mau\s+mo\s+ta|viet\s+mo\s+ta)\b", normalized)
        or re.search(r"\b(dien|ghi|bo\s+sung)\s+(gi|nhung\s+gi|thong\s+tin\s+gi|thong\s+tin\s+nao)\b", normalized)
    )


def _is_ticket_draft_detail_update(normalized: str) -> bool:
    if not normalized:
        return False
    if _is_ticket_draft_guidance_question(normalized):
        return False
    if re.search(r"\b(tao|mo|gui|lap)\s+(ticket|phieu|yeu\s+cau)\b", normalized):
        return bool(re.search(r"\b(bo\s+sung|them|cap\s+nhat|dien|mo\s+ta)\b", normalized))
    if _looks_like_policy_or_general_question(normalized):
        return False
    return len(re.findall(r"[a-z0-9]{2,}", normalized)) >= 2


def _ticket_draft_guidance_answer(draft: PendingTicketDraft) -> str:
    suggestions = _ticket_suggestion_lines(draft.suggested_fields)
    return (
        "Bạn có thể bổ sung các thông tin dưới đây bằng cách chat từng ý, mình sẽ tự cập nhật vào mô tả nháp ticket:\n"
        f"{suggestions}"
    )


def _ticket_draft_need_detail_answer(draft: PendingTicketDraft) -> str:
    suggestions = _ticket_suggestion_lines(draft.suggested_fields)
    return (
        "Mình đã chọn đúng mục cần bổ sung. Bạn nhập thông tin cụ thể sau dấu hai chấm rồi gửi, "
        "mình sẽ cập nhật vào mô tả nháp ticket.\n"
        f"{suggestions}"
    )


def _ticket_draft_updated_answer(draft: PendingTicketDraft) -> str:
    suggestions = _ticket_suggestion_lines(draft.suggested_fields)
    return (
        "Mình đã cập nhật thông tin bạn vừa cung cấp vào nháp ticket. "
        "Bạn kiểm tra lại card bên dưới; nếu còn thiếu, bạn có thể chat thêm các ý này:\n"
        f"{suggestions}"
    )


def _ticket_suggestion_lines(suggested_fields: list[str]) -> str:
    suggestions = suggested_fields or suggest_ticket_details("other", "")
    return "\n".join(f"- {item}" for item in suggestions[:4])


def _ticket_draft_ready_answer(title: str, description: str, suggested_fields: list[str] | None = None) -> str:
    normalized = _normalize(f"{title} {description}")
    if "cham luong" in normalized or "tre luong" in normalized or "chua nhan luong" in normalized:
        month_match = re.search(r"\bthang\s+([0-9]{1,2})\b", normalized)
        suffix = f" tháng {month_match.group(1)}" if month_match else ""
        return (
            f"Mình đã chuẩn bị nháp ticket cho vấn đề chậm lương{suffix}. "
            "Bạn kiểm tra lại thông tin bên dưới rồi bấm Gửi yêu cầu nếu đã đúng nhé."
        )
    return "Mình đã điền sẵn thông tin ticket. Bạn kiểm tra lại rồi bấm gửi yêu cầu nhé."


def _citation_context_summary(citations) -> str:
    summaries = []
    for citation in citations[:3]:
        title = getattr(citation, "document_title", "")
        section = getattr(citation, "section", "")
        summaries.append(" - ".join(part for part in [title, section] if part))
    return "\n".join(summaries)


def _output_context_summary(state: AgentState, citations) -> str:
    summaries = []
    citation_summary = _citation_context_summary(citations)
    if citation_summary:
        summaries.append(citation_summary)
    topic_scope = state.get("topic_scope") or {}
    topic = topic_scope.get("topic")
    if topic:
        summaries.append(f"Topic classification: {topic}")
    actions = state.get("actions", [])
    if _has_action_type(actions, "hr_metric_lookup"):
        summaries.append("Tool result confirmed: HRIS personal metrics lookup completed for the authenticated user.")
    if _has_action_type(actions, "ticket_draft_confirmation"):
        summaries.append("Tool result confirmed: a prefilled HR ticket draft is ready for user review, not submitted yet.")
    if _has_action_type(actions, "escalation_confirmation_required"):
        summaries.append("Tool result confirmed: HR escalation confirmation is required before ticket submission.")
    return "\n".join(summaries)


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
        "mo ta chi tiet van de",
        "van de can hr ho tro",
        "dien form ticket",
        "cung cap them thong tin de minh tao ticket",
        "minh tao ticket nhe",
    ]
    has_pending_prompt = any(marker in normalized for marker in pending_markers) or (
        ("noi dung" in normalized or "mo ta" in normalized) and "ticket" in normalized
    )
    has_recent_ticket_request = "ticket" in normalized and any(phrase in normalized for phrase in {"tao ticket", "t o ticket"})
    return has_pending_prompt or (has_recent_ticket_request and _has_ticket_description(query))


def _is_bare_numeric_reply_without_pending_choice(query: str, conversation_context: str | None = None) -> bool:
    if not re.fullmatch(r"\s*\d{1,2}\s*", str(query or "")):
        return False
    normalized_context = _normalize(conversation_context or "")
    pending_choice_markers = {
        "chon mot",
        "chon so",
        "vui long chon",
        "nhap so",
        "lua chon",
        "xac nhan gui ticket",
        "xac nhan",
    }
    return not any(marker in normalized_context for marker in pending_choice_markers)


def _bare_numeric_choice_message() -> str:
    return (
        "Mình chưa thấy danh sách lựa chọn nào đang chờ chọn bằng số. "
        "Bạn vui lòng nhập rõ câu hỏi HR, ví dụ: chính sách nghỉ phép, bảo hiểm, phúc lợi, hợp đồng hoặc tạo ticket cho HR."
    )


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


def _format_hr_metrics_answer(query: str, metrics) -> str:
    fields = _requested_hr_metric_fields(query) or ["leave", "insurance", "reward"]
    parts: list[str] = []
    if "leave" in fields:
        parts.append(f"Số ngày phép còn lại của bạn là {metrics.leave_days_remaining}.")
    if "insurance" in fields:
        parts.append(f"Trạng thái bảo hiểm của bạn là {_display_label(metrics.insurance_status)}.")
    if "reward" in fields:
        parts.append(f"Xét duyệt khen thưởng của bạn là {_display_label(metrics.reward_review_status)}.")
    return " ".join(parts)


def _requested_hr_metric_fields(query: str) -> list[str]:
    normalized = _normalize(query)
    fields: list[str] = []
    if re.search(r"\b(ngay\s+phep|nghi\s+phep|phep\s+nam|leave)\b", normalized):
        fields.append("leave")
    if re.search(r"\b(bao\s+hiem|insurance)\b", normalized):
        fields.append("insurance")
    if re.search(r"\b(khen\s+thuong|xet\s+duyet|reward|review)\b", normalized):
        fields.append("reward")
    return fields
