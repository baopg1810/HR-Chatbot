import asyncio
import json
from datetime import datetime, timezone
from time import perf_counter
from uuid import uuid4
from fastapi import APIRouter, Depends, Header, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from langfuse import get_client, propagate_attributes

from app.agents.graph import agent
from app.agents.nodes.example_node import (
    classify_intent_node,
    guardrail_node,
    handle_no_source_node,
    handle_ticket_intent_node,
    hr_metrics_node,
    retrieve_policy_node,
    route_retrieval,
)
from app.schemas.schemas import ChatRequest, ChatResponse
from app.models.schemas import ChatAction
from app.models.user import User
from app.api.deps import get_current_user_from_authorization_header
from app.database.session import get_db

from app.services.llm import build_conversation_context, stream_cited_answer, stream_general_answer
from app.services.trending import record_chat_query
from app.services.rate_limit import enforce_chat_rate_limit

router = APIRouter()


async def _save_user_message(current_user: User, session_id: str, message: str, db: AsyncSession) -> None:
    from app.models.chat import ChatMessage, ChatSession
    from app.services.tickets import safe_parse_uuid

    user_uuid = safe_parse_uuid(current_user.id)
    session_uuid = safe_parse_uuid(session_id)
    if not user_uuid or not session_uuid:
        return

    title = _chat_session_title(message)
    db_session = await db.get(ChatSession, session_uuid)
    if db_session is None:
        db_session = ChatSession(id=session_uuid, user_id=user_uuid, title=title)
        db.add(db_session)
    elif not db_session.title or db_session.title == "Chat Session":
        db_session.title = title

    stmt = select(ChatMessage).filter(
        ChatMessage.session_id == session_uuid,
        ChatMessage.role == "user",
        ChatMessage.content == message,
    )
    result = await db.execute(stmt)
    if result.scalars().first() is None:
        db.add(
            ChatMessage(
                id=uuid4(),
                session_id=session_uuid,
                user_id=user_uuid,
                role="user",
                content=message,
                created_at=datetime.now(timezone.utc),
                citations=[],
            )
        )
    await db.commit()


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> ChatResponse:
    """Return a contract-shaped scaffold chat response for the authenticated user."""
    current_user = await get_current_user_from_authorization_header(authorization, db)
    enforce_chat_rate_limit(str(current_user.id))
    session_id = request.session_id or f"session-{uuid4()}"
    message_id = f"msg-{uuid4()}"
    langfuse = get_client()
    with propagate_attributes(user_id=str(current_user.id), session_id=session_id):
        with langfuse.start_as_current_observation(
            name="chat",
            input=request.message,
            metadata={"user_email": current_user.email},
        ) as trace:
            conversation_context = await _load_session_conversation_context(current_user, session_id, db)
            await _save_user_message(current_user, session_id, request.message, db)
            response = await _build_chat_response(
                current_user,
                request,
                session_id=session_id,
                message_id=message_id,
                conversation_context=conversation_context,
                db=db,
            )
            trace.update(output=response.answer)
            return response


@router.post("/chat/stream")
async def chat_stream(
    request: ChatRequest,
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """Stream a chat response as Server-Sent Events while preserving the normal chat contract."""

    current_user = await get_current_user_from_authorization_header(authorization, db)
    enforce_chat_rate_limit(str(current_user.id))
    session_id = request.session_id or f"session-{uuid4()}"
    message_id = f"msg-{uuid4()}"
    return StreamingResponse(
        _stream_live_chat_response(current_user, request, session_id=session_id, message_id=message_id, db=db),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


async def _stream_live_chat_response(
    current_user: User,
    request: ChatRequest,
    *,
    session_id: str,
    message_id: str,
    db: AsyncSession,
):
    stream_started_perf = perf_counter()
    first_token_sent = False
    langfuse = get_client()
    with propagate_attributes(user_id=str(current_user.id), session_id=session_id):
        with langfuse.start_as_current_observation(
            name="chat_stream",
            input=request.message,
            metadata={"user_email": current_user.email},
        ) as trace:
            yield _sse_event("start", {"message_id": message_id, "session_id": session_id})
            try:
                conversation_context = await _load_session_conversation_context(current_user, session_id, db)
                await _save_user_message(current_user, session_id, request.message, db)
                answer_chunks: list[str] = []
                response: ChatResponse | None = None

                async for stream_item in _stream_chat_answer_chunks(
                    current_user,
                    request,
                    session_id=session_id,
                    message_id=message_id,
                    conversation_context=conversation_context,
                    db=db,
                ):
                    if "response" in stream_item:
                        response = stream_item["response"]
                        continue
                    text = stream_item["text"]
                    if not first_token_sent:
                        trace.update(
                            metadata={
                                "time_to_first_token_ms": round((perf_counter() - stream_started_perf) * 1000, 2),
                                "time_to_first_token_source": "sse_live_token",
                            }
                        )
                        first_token_sent = True
                    answer_chunks.append(text)
                    yield _sse_event("token", {"text": text})
                    await asyncio.sleep(0)

                if response is None:
                    response = ChatResponse(
                        message_id=message_id,
                        session_id=session_id,
                        answer="".join(answer_chunks),
                        citations=[],
                        actions=[_no_action()],
                    )
                response = await _record_and_return_chat(current_user, request, response)
                trace.update(output=response.answer)
                yield _sse_event("done", response.model_dump(mode="json"))
            except Exception as exc:
                trace.update(metadata={"stream_error": exc.__class__.__name__}, output=str(exc))
                yield _sse_event("error", {"detail": "Không thể stream câu trả lời."})


async def _stream_chat_answer_chunks(
    current_user: User,
    request: ChatRequest,
    *,
    session_id: str,
    message_id: str,
    conversation_context: str,
    db: AsyncSession,
):
    state = {
        "query": request.message,
        "current_user": current_user,
        "session_id": session_id,
        "message_id": message_id,
        "conversation_context": conversation_context,
        "db": db,
    }

    state.update(await guardrail_node(state))
    if state.get("intent") == "blocked":
        response = _response_from_state(state, message_id=message_id, session_id=session_id)
        async for chunk in _stream_finished_answer_chunks(response):
            yield chunk
        yield {"response": response}
        return

    state.update(await classify_intent_node(state))
    intent = state.get("intent", "general")
    if intent == "hr_metric":
        state.update(await hr_metrics_node(state))
        response = _response_from_state(state, message_id=message_id, session_id=session_id)
        async for chunk in _stream_finished_answer_chunks(response):
            yield chunk
        yield {"response": response}
        return

    if intent == "ticket_create":
        state.update(await handle_ticket_intent_node(state))
        response = _response_from_state(state, message_id=message_id, session_id=session_id)
        async for chunk in _stream_finished_answer_chunks(response):
            yield chunk
        yield {"response": response}
        return

    if intent == "policy_question":
        state.update(await retrieve_policy_node(state))
        route = route_retrieval(state)
        if route == "answer_with_sources":
            citations = state.get("citations", [])
            answer = ""
            for token in stream_cited_answer(request.message, citations, conversation_context=conversation_context):
                answer += token
                yield {"text": token}
                await asyncio.sleep(0)
            yield {
                "response": ChatResponse(
                    message_id=message_id,
                    session_id=session_id,
                    answer=answer,
                    citations=citations,
                    actions=[_no_action()],
                )
            }
            return
        if route == "handle_no_source":
            state.update(await handle_no_source_node(state))
            response = _response_from_state(state, message_id=message_id, session_id=session_id)
            async for chunk in _stream_finished_answer_chunks(response):
                yield chunk
            yield {"response": response}
            return

    user_name = getattr(current_user, "full_name", "bạn")
    answer = ""
    for token in stream_general_answer(request.message, user_name, conversation_context=conversation_context):
        answer += token
        yield {"text": token}
        await asyncio.sleep(0)
    yield {
        "response": ChatResponse(
            message_id=message_id,
            session_id=session_id,
            answer=answer,
            citations=[],
            actions=[_no_action()],
        )
    }


def _response_from_state(state: dict, *, message_id: str, session_id: str) -> ChatResponse:
    return ChatResponse(
        message_id=message_id,
        session_id=session_id,
        answer=str(state.get("answer") or "Tôi chưa thể xử lý yêu cầu này."),
        citations=state.get("citations", []),
        actions=state.get("actions", [_no_action()]),
        escalated_ticket_id=state.get("escalated_ticket_id"),
        refusal_reason=state.get("refusal_reason"),
    )


def _no_action() -> ChatAction:
    return ChatAction(type="none", label="Không cần thao tác", data=None)


async def _stream_finished_answer_chunks(response: ChatResponse):
    for chunk in _text_chunks(response.answer):
        yield {"text": chunk}
        await asyncio.sleep(0)


async def _load_session_conversation_context(current_user: User, session_id: str, db: AsyncSession) -> str:
    from app.models.chat import ChatMessage, ChatSession
    from app.services.tickets import safe_parse_uuid

    user_uuid = safe_parse_uuid(current_user.id)
    session_uuid = safe_parse_uuid(session_id)
    if not user_uuid or not session_uuid:
        return ""

    db_session = await db.get(ChatSession, session_uuid)
    if db_session is None or db_session.user_id != user_uuid:
        return ""

    stmt = (
        select(ChatMessage.role, ChatMessage.content)
        .filter(ChatMessage.session_id == session_uuid)
        .order_by(ChatMessage.created_at.asc())
    )
    result = await db.execute(stmt)
    return build_conversation_context([(role, content) for role, content in result.all()])


async def _build_chat_response(
    current_user: User,
    request: ChatRequest,
    *,
    session_id: str,
    message_id: str,
    conversation_context: str = "",
    db: AsyncSession | None = None,
) -> ChatResponse:
    result = await agent.ainvoke(
        {
            "query": request.message,
            "current_user": current_user,
            "session_id": session_id,
            "message_id": message_id,
            "conversation_context": conversation_context,
            "db": db,
        }
    )
    response = result.get("response")
    if not isinstance(response, ChatResponse):
        response = ChatResponse(
            message_id=message_id,
            session_id=session_id,
            answer=str(result.get("answer") or "Tôi chưa thể xử lý yêu cầu này."),
            citations=result.get("citations", []),
            actions=result.get("actions", []),
            escalated_ticket_id=result.get("escalated_ticket_id"),
            refusal_reason=result.get("refusal_reason"),
        )
    return await _record_and_return_chat(
        current_user=current_user,
        request=request,
        response=response,
    )


async def _stream_chat_response(response: ChatResponse):
    yield _sse_event("start", {"message_id": response.message_id, "session_id": response.session_id})
    async for event in _stream_finished_response(response):
        yield event


def _sse_event(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


async def _stream_finished_response(response: ChatResponse):
    for chunk in _text_chunks(response.answer):
        yield _sse_event("token", {"text": chunk})
        await asyncio.sleep(0)
    yield _sse_event("done", response.model_dump(mode="json"))


def _text_chunks(text: str, *, target_chars: int = 48) -> list[str]:
    words = text.split(" ")
    chunks: list[str] = []
    current = ""
    for word in words:
        next_value = word if not current else f"{current} {word}"
        if current and len(next_value) > target_chars:
            chunks.append(current + " ")
            current = word
        else:
            current = next_value
    if current:
        chunks.append(current)
    return chunks or [""]


@router.get("/status")
async def agent_status():
    """Kiểm tra trạng thái agent."""
    return {"status": "ready", "agent": "HR Helpdesk AI scaffold"}


@router.get("/chat/sessions")
async def get_chat_sessions(
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve all chat sessions for the authenticated user."""
    current_user = await get_current_user_from_authorization_header(authorization, db)

    from app.models.chat import ChatSession
    from app.services.tickets import safe_parse_uuid

    user_uuid = safe_parse_uuid(current_user.id)
    if not user_uuid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user ID format")

    stmt = select(ChatSession).filter(ChatSession.user_id == user_uuid).order_by(ChatSession.updated_at.desc())
    result = await db.execute(stmt)
    sessions = result.scalars().all()

    return [
        {
            "id": f"session-{session.id}",
            "user_id": str(session.user_id),
            "title": session.title or "Chat Session",
            "created_at": session.created_at.isoformat() if session.created_at else None,
            "updated_at": session.updated_at.isoformat() if session.updated_at else None,
        }
        for session in sessions
    ]


@router.get("/chat/sessions/{session_id}/messages")
async def get_chat_session_messages(
    session_id: str,
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve all messages in a specific chat session for the authenticated user."""
    current_user = await get_current_user_from_authorization_header(authorization, db)

    from app.models.chat import ChatMessage, ChatSession
    from app.services.tickets import safe_parse_uuid

    user_uuid = safe_parse_uuid(current_user.id)
    session_uuid = safe_parse_uuid(session_id)
    if not user_uuid or not session_uuid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid ID format")

    session = await db.get(ChatSession, session_uuid)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy cuộc trò chuyện")

    if session.user_id != user_uuid and current_user.role not in {"hr_admin", "admin"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn không có quyền truy cập lịch sử cuộc trò chuyện này",
        )

    stmt = select(ChatMessage).filter(ChatMessage.session_id == session_uuid).order_by(ChatMessage.created_at.asc())
    result = await db.execute(stmt)
    messages = result.scalars().all()

    return [
        {
            "id": str(message.id),
            "sender": "ai" if message.role == "assistant" else "user",
            "text": message.content,
            "timestamp": message.created_at.isoformat() if message.created_at else None,
            "citations": message.citations or [],
        }
        for message in messages
    ]


async def _record_and_return_chat(current_user: User, request: ChatRequest, response: ChatResponse) -> ChatResponse:
    await record_chat_query(
        message_id=response.message_id,
        user_id=current_user.id,
        query=request.message,
        citations=response.citations,
        session_id=response.session_id,
        answer=response.answer,
    )
    
    from app.database.session import get_db_context
    from app.models.chat import ChatSession, ChatMessage
    from app.services.tickets import safe_parse_uuid
    
    user_uuid = safe_parse_uuid(current_user.id)
    session_uuid = safe_parse_uuid(response.session_id)
    msg_uuid = safe_parse_uuid(response.message_id)
    
    if user_uuid and session_uuid and msg_uuid:
        try:
            async with get_db_context() as db:
                db_session = await db.get(ChatSession, session_uuid)
                if not db_session:
                    db_session = ChatSession(
                        id=session_uuid,
                        user_id=user_uuid,
                        title=_chat_session_title(request.message)
                    )
                    db.add(db_session)
                elif not db_session.title or db_session.title == "Chat Session":
                    db_session.title = _chat_session_title(request.message)
                
                citations_list = []
                if response.citations:
                    for c in response.citations:
                        if hasattr(c, "model_dump"):
                            citations_list.append(c.model_dump())
                        elif isinstance(c, dict):
                            citations_list.append(c)
                        else:
                            citations_list.append(str(c))
                
                db_msg = ChatMessage(
                    id=msg_uuid,
                    session_id=session_uuid,
                    user_id=user_uuid,
                    role="assistant",
                    content=response.answer,
                    created_at=datetime.now(timezone.utc),
                    citations=citations_list
                )
                db.add(db_msg)
                await db.commit()
        except Exception as e:
            print(f"Error saving assistant message to DB: {e}")
            
    return response


def _chat_session_title(message: str) -> str:
    return message[:30] + "..." if len(message) > 30 else message


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
