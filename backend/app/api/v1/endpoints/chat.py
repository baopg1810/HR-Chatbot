import asyncio
import json
from uuid import uuid4
from fastapi import APIRouter, Depends, Header, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.schemas import ChatRequest, ChatResponse, ChatAction
from app.models.user import User
from app.api.deps import get_current_user_from_authorization_header
from app.database.session import get_db

from app.services.hris import get_personal_hr_metrics, is_hr_metric_query
from app.services.guardrails import evaluate_chat_guardrails, looks_like_hr_question
from app.services.llm import (
    build_cited_answer,
    build_general_answer,
    build_refusal_answer,
    stream_cited_answer,
    stream_general_answer,
)
from app.services.retrieval import search_policy_chunks, user_has_readable_chunks
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
    await _save_user_message(current_user, session_id, request.message, db)
    return await _build_chat_response(current_user, request, session_id=session_id, message_id=message_id)


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
    await _save_user_message(current_user, session_id, request.message, db)
    return StreamingResponse(
        _stream_chat_response(current_user, request, session_id=session_id, message_id=message_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


async def _build_chat_response(current_user: User, request: ChatRequest, *, session_id: str, message_id: str) -> ChatResponse:
    if is_hr_metric_query(request.message):
        metrics = get_personal_hr_metrics(current_user)
        return await _record_and_return_chat(
            current_user=current_user,
            request=request,
            response=ChatResponse(
                message_id=message_id,
                session_id=session_id,
                answer=(
                    f"Số ngày phép còn lại của bạn là {metrics.leave_days_remaining}. "
                    f"Trạng thái bảo hiểm: {_display_label(metrics.insurance_status)}. "
                    f"Xét duyệt khen thưởng: {_display_label(metrics.reward_review_status)}."
                ),
                citations=[],
                actions=[
                    ChatAction(
                        type="hr_metric_lookup",
                        label="Số liệu nhân sự cá nhân",
                        data=metrics.model_dump(),
                    )
                ],
                escalated_ticket_id=None,
                refusal_reason=None,
            ),
        )

    guardrail = evaluate_chat_guardrails(request.message)
    if not guardrail.allowed and guardrail.refusal_reason is not None:
        ticket_id = None
        actions = [ChatAction(type="none", label="Không cần thao tác", data=None)]
        if guardrail.refusal_reason == "outside_scope":
            actions = [
                ChatAction(
                    type="escalation_confirmation_required",
                    label="Đã tạo ticket chuyển HR",
                    data={
                        "message": request.message,
                        "reason": guardrail.refusal_reason,
                        "priority": "normal",
                        "session_id": session_id,
                    },
                )
            ]
            actions[0].label = "Cần xác nhận gửi ticket cho HR"
        return await _record_and_return_chat(
            current_user=current_user,
            request=request,
            response=ChatResponse(
                message_id=message_id,
                session_id=session_id,
                answer=(
                    f"{build_refusal_answer(guardrail.refusal_reason)}\n\n"
                    "Bạn có muốn gửi ticket cho HR để được hỗ trợ tiếp không?"
                    if guardrail.refusal_reason == "outside_scope"
                    else build_refusal_answer(guardrail.refusal_reason)
                ),
                citations=[],
                actions=actions,
                escalated_ticket_id=ticket_id,
                refusal_reason=guardrail.refusal_reason,
            ),
        )

    citations = search_policy_chunks(request.message, current_user)
    if citations:
        answer = build_cited_answer(request.message, citations)
        refusal_reason = None
    elif user_has_readable_chunks(current_user) and looks_like_hr_question(request.message):
        answer = (
            f"{build_refusal_answer('no_source')}\n\n"
            "Bạn có muốn gửi ticket cho HR để được hỗ trợ tiếp không?"
        )
        refusal_reason = "no_source"
        actions = [
            ChatAction(
                type="escalation_confirmation_required",
                label="Đã tạo ticket chuyển HR",
                data={
                    "message": request.message,
                    "reason": "no_source",
                    "priority": "normal",
                    "session_id": session_id,
                },
            )
        ]
        actions[0].label = "Cần xác nhận gửi ticket cho HR"
        escalated_ticket_id = None
    else:
        answer = build_general_answer(request.message, current_user.full_name)
        refusal_reason = None
        actions = [ChatAction(type="none", label="Không cần thao tác", data=None)]
        escalated_ticket_id = None
    if citations:
        actions = [ChatAction(type="none", label="Không cần thao tác", data=None)]
        escalated_ticket_id = None
    return await _record_and_return_chat(
        current_user=current_user,
        request=request,
        response=ChatResponse(
            message_id=message_id,
            session_id=session_id,
            answer=answer,
            citations=citations,
            actions=actions,
            escalated_ticket_id=escalated_ticket_id,
            refusal_reason=refusal_reason,
        ),
    )


async def _stream_chat_response(current_user: User, request: ChatRequest, *, session_id: str, message_id: str):
    yield _sse_event("start", {"message_id": message_id, "session_id": session_id})
    try:
        if is_hr_metric_query(request.message):
            response = await _build_chat_response(
                current_user,
                request,
                session_id=session_id,
                message_id=message_id,
            )
            async for event in _stream_finished_response(response):
                yield event
            return

        guardrail = evaluate_chat_guardrails(request.message)
        if not guardrail.allowed and guardrail.refusal_reason is not None:
            response = await _build_chat_response(
                current_user,
                request,
                session_id=session_id,
                message_id=message_id,
            )
            async for event in _stream_finished_response(response):
                yield event
            return

        citations = await asyncio.to_thread(search_policy_chunks, request.message, current_user)
        if citations:
            answer = ""
            stream = iter(stream_cited_answer(request.message, citations))
            while True:
                token = await asyncio.to_thread(_next_stream_token, stream)
                if token is None:
                    break
                answer += token
                yield _sse_event("token", {"text": token})
                await asyncio.sleep(0)
            response = await _record_and_return_chat(
                current_user=current_user,
                request=request,
                response=ChatResponse(
                    message_id=message_id,
                    session_id=session_id,
                    answer=answer,
                    citations=citations,
                    actions=[ChatAction(type="none", label="Không cần thao tác", data=None)],
                    escalated_ticket_id=None,
                    refusal_reason=None,
                ),
            )
            yield _sse_event("done", response.model_dump(mode="json"))
            return

        has_readable_chunks = await asyncio.to_thread(user_has_readable_chunks, current_user)
        if has_readable_chunks and looks_like_hr_question(request.message):
            response = await _build_chat_response(
                current_user,
                request,
                session_id=session_id,
                message_id=message_id,
            )
            async for event in _stream_finished_response(response):
                yield event
            return

        answer = ""
        stream = iter(stream_general_answer(request.message, current_user.full_name))
        while True:
            token = await asyncio.to_thread(_next_stream_token, stream)
            if token is None:
                break
            answer += token
            yield _sse_event("token", {"text": token})
            await asyncio.sleep(0)
        response = await _record_and_return_chat(
            current_user=current_user,
            request=request,
            response=ChatResponse(
                message_id=message_id,
                session_id=session_id,
                answer=answer,
                citations=[],
                actions=[ChatAction(type="none", label="Không cần thao tác", data=None)],
                escalated_ticket_id=None,
                refusal_reason=None,
            ),
        )
        yield _sse_event("done", response.model_dump(mode="json"))
    except Exception as exc:
        yield _sse_event("error", {"detail": str(exc) or "Unable to stream chat response"})


def _sse_event(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


async def _stream_finished_response(response: ChatResponse):
    for chunk in _text_chunks(response.answer):
        yield _sse_event("token", {"text": chunk})
        await asyncio.sleep(0)
    yield _sse_event("done", response.model_dump(mode="json"))


def _next_stream_token(stream) -> str | None:
    try:
        return next(stream)
    except StopIteration:
        return None


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
