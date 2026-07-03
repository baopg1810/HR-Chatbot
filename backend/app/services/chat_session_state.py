from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from pydantic import ValidationError

from app.database.session import get_db_context
from app.models.chat_session_state import ChatSessionState
from app.models.schemas import ChatWorkflowState
from app.services.tickets import safe_parse_uuid

logger = logging.getLogger(__name__)


async def get_chat_session_state(db: Any, session_id: str) -> ChatWorkflowState:
    session_uuid = safe_parse_uuid(session_id)
    if session_uuid is None:
        return ChatWorkflowState()

    row = await db.get(ChatSessionState, session_uuid)
    if row is None:
        return ChatWorkflowState()

    try:
        return ChatWorkflowState.model_validate(row.state_json or {})
    except ValidationError:
        logger.warning("Invalid chat session workflow state; using default state.")
        return ChatWorkflowState()


async def save_chat_session_state(
    db: Any | None,
    session_id: str,
    state: ChatWorkflowState,
) -> ChatWorkflowState:
    if db is None:
        async with get_db_context() as session:
            return await save_chat_session_state(session, session_id, state)

    session_uuid = safe_parse_uuid(session_id)
    if session_uuid is None:
        return ChatWorkflowState()

    row = await db.get(ChatSessionState, session_uuid)
    payload = state.model_dump(mode="json")
    if row is None:
        row = ChatSessionState(session_id=session_uuid, state_json=payload)
        db.add(row)
    else:
        row.state_json = payload
        row.updated_at = datetime.now(timezone.utc)
    await db.commit()
    return state


async def clear_chat_session_state(db: Any | None, session_id: str) -> ChatWorkflowState:
    if db is None:
        async with get_db_context() as session:
            return await clear_chat_session_state(session, session_id)

    previous_state = None
    if db is not None:
        previous_state = await get_chat_session_state(db, session_id)
    default_state = preserve_conversation_memory(ChatWorkflowState(), previous_state)
    return await save_chat_session_state(db, session_id, default_state)


def preserve_conversation_memory(
    state: ChatWorkflowState,
    previous_state: ChatWorkflowState | dict | None,
) -> ChatWorkflowState:
    if previous_state is None:
        return state
    if isinstance(previous_state, dict):
        previous_state = ChatWorkflowState.model_validate(previous_state)
    return state.model_copy(
        update={
            "conversation_summary": previous_state.conversation_summary,
            "conversation_summary_message_count": previous_state.conversation_summary_message_count,
            "conversation_summary_updated_at": previous_state.conversation_summary_updated_at,
        }
    )


def default_ticket_draft_state(session_id: str, previous_state: ChatWorkflowState | dict | None = None) -> ChatWorkflowState:
    from app.models.schemas import PendingTicketDraft

    state = ChatWorkflowState(
        active_flow="ticket_draft",
        pending_ticket_draft=PendingTicketDraft(
            session_id=session_id,
            missing_fields=["title", "category", "description"],
        ),
        last_intent="ticket_create",
    )
    return preserve_conversation_memory(state, previous_state)
