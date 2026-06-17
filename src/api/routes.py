import asyncio
import json
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Query, UploadFile, status
from fastapi.responses import StreamingResponse

from src.models.schemas import (
    ChatAction,
    ChatRequest,
    ChatResponse,
    DocumentCreate,
    DocumentIngestResult,
    DocumentListResponse,
    EscalationCreate,
    FeedbackCreate,
    FeedbackResponse,
    LoginRequest,
    LoginResponse,
    LogoutRequest,
    LogoutResponse,
    PersonalHrMetrics,
    Ticket,
    TicketListResponse,
    TicketPriority,
    TicketStatus,
    TicketUpdate,
    TokenRefreshRequest,
    TokenResponse,
    TrendPinsResponse,
    TrendRunRequest,
    TrendRunResponse,
    User,
)
from src.services.auth import (
    get_current_user,
    issue_token_pair,
    refresh_token_pair,
    revoke_refresh_token,
    user_from_authorization_header,
)
from src.services.demo_users import authenticate_demo_user
from src.services.documents import create_document, create_document_from_upload, delete_document, list_documents
from src.services.feedback import create_feedback
from src.services.guardrails import evaluate_chat_guardrails, looks_like_hr_question
from src.services.hris import get_personal_hr_metrics, is_hr_metric_query
from src.services.llm import (
    build_cited_answer,
    build_general_answer,
    build_refusal_answer,
    stream_cited_answer,
    stream_general_answer,
)
from src.services.retrieval import search_policy_chunks, user_has_readable_chunks
from src.services.tickets import create_ticket, create_ticket_from_chat, list_tickets, update_ticket
from src.services.trending import list_trend_pins, record_chat_query, run_trending

router = APIRouter()


@router.post("/auth/login", response_model=LoginResponse)
async def login(request: LoginRequest) -> LoginResponse:
    user = authenticate_demo_user(request.email, request.password)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Thông tin đăng nhập không hợp lệ")
    access_token, refresh_token = issue_token_pair(user)
    return LoginResponse(access_token=access_token, refresh_token=refresh_token, user=user)


@router.post("/auth/refresh", response_model=TokenResponse)
async def refresh_auth_token(request: TokenRefreshRequest) -> TokenResponse:
    access_token, refresh_token = refresh_token_pair(request.refresh_token)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/auth/logout", response_model=LogoutResponse)
async def logout(request: LogoutRequest) -> LogoutResponse:
    revoked = revoke_refresh_token(request.refresh_token)
    if not revoked:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Refresh token already revoked or invalid")
    return LogoutResponse()


@router.get("/me", response_model=User)
async def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.get("/me/hr-metrics", response_model=PersonalHrMetrics)
async def my_hr_metrics(current_user: User = Depends(get_current_user)) -> PersonalHrMetrics:
    return get_personal_hr_metrics(current_user)


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, authorization: str | None = Header(default=None)) -> ChatResponse:
    """Return a contract-shaped scaffold chat response for the authenticated user."""
    current_user = user_from_authorization_header(authorization)
    session_id = request.session_id or f"session-{uuid4()}"
    message_id = f"msg-{uuid4()}"
    return _build_chat_response(current_user, request, session_id=session_id, message_id=message_id)


@router.post("/chat/stream")
async def chat_stream(request: ChatRequest, authorization: str | None = Header(default=None)) -> StreamingResponse:
    """Stream a chat response as Server-Sent Events while preserving the normal chat contract."""
    current_user = user_from_authorization_header(authorization)
    session_id = request.session_id or f"session-{uuid4()}"
    message_id = f"msg-{uuid4()}"
    return StreamingResponse(
        _stream_chat_response(current_user, request, session_id=session_id, message_id=message_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


def _build_chat_response(current_user: User, request: ChatRequest, *, session_id: str, message_id: str) -> ChatResponse:
    if is_hr_metric_query(request.message):
        metrics = get_personal_hr_metrics(current_user)
        return _record_and_return_chat(
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
        if guardrail.refusal_reason in {"outside_scope", "sensitive"}:
            ticket = create_ticket_from_chat(
                current_user,
                request.message,
                reason=guardrail.refusal_reason,
                priority="high" if guardrail.refusal_reason == "sensitive" else "normal",
                session_id=session_id,
            )
            ticket_id = ticket.id
            actions = [
                ChatAction(
                    type="escalation_created",
                    label="Đã tạo ticket chuyển HR",
                    data={"ticket_id": ticket.id, "status": ticket.status},
                )
            ]
        return _record_and_return_chat(
            current_user=current_user,
            request=request,
            response=ChatResponse(
            message_id=message_id,
            session_id=session_id,
            answer=build_refusal_answer(guardrail.refusal_reason),
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
        ticket = create_ticket_from_chat(
            current_user,
            request.message,
            reason="no_source",
            priority="normal",
            session_id=session_id,
        )
        answer = build_refusal_answer("no_source")
        refusal_reason = "no_source"
        actions = [
            ChatAction(
                type="escalation_created",
                label="Đã tạo ticket chuyển HR",
                data={"ticket_id": ticket.id, "status": ticket.status},
            )
        ]
        escalated_ticket_id = ticket.id
    else:
        answer = build_general_answer(request.message, current_user.full_name)
        refusal_reason = None
        actions = [ChatAction(type="none", label="Không cần thao tác", data=None)]
        escalated_ticket_id = None
    if citations:
        actions = [ChatAction(type="none", label="Không cần thao tác", data=None)]
        escalated_ticket_id = None
    return _record_and_return_chat(
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
            response = await asyncio.to_thread(
                _build_chat_response,
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
            response = await asyncio.to_thread(
                _build_chat_response,
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
            response = _record_and_return_chat(
                current_user=current_user,
                request=request,
                response=ChatResponse(
                    message_id=message_id,
                    session_id=session_id,
                    answer=answer,
                    citations=citations,
                    actions=[ChatAction(type="none", label="KhÃ´ng cáº§n thao tÃ¡c", data=None)],
                    escalated_ticket_id=None,
                    refusal_reason=None,
                ),
            )
            yield _sse_event("done", response.model_dump(mode="json"))
            return

        has_readable_chunks = await asyncio.to_thread(user_has_readable_chunks, current_user)
        if has_readable_chunks and looks_like_hr_question(request.message):
            response = await asyncio.to_thread(
                _build_chat_response,
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
        response = _record_and_return_chat(
            current_user=current_user,
            request=request,
            response=ChatResponse(
                message_id=message_id,
                session_id=session_id,
                answer=answer,
                citations=[],
                actions=[ChatAction(type="none", label="KhÃ´ng cáº§n thao tÃ¡c", data=None)],
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


@router.post("/escalations", response_model=Ticket)
async def create_escalation(
    request: EscalationCreate,
    current_user: User = Depends(get_current_user),
) -> Ticket:
    return create_ticket(current_user, request)


@router.get("/admin/tickets", response_model=TicketListResponse)
async def admin_tickets(
    status_filter: TicketStatus | None = Query(default=None, alias="status"),
    priority: TicketPriority | None = Query(default=None),
    current_user: User = Depends(get_current_user),
) -> TicketListResponse:
    _require_hr_admin(current_user)
    return TicketListResponse(tickets=list_tickets(status=status_filter, priority=priority))


@router.patch("/admin/tickets/{ticket_id}", response_model=Ticket)
async def patch_ticket(
    ticket_id: str,
    request: TicketUpdate,
    current_user: User = Depends(get_current_user),
) -> Ticket:
    _require_hr_admin(current_user)
    ticket = update_ticket(
        ticket_id,
        status=request.status,
        assignee_id=request.assignee_id,
        internal_note=request.internal_note,
    )
    if ticket is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy ticket")
    return ticket


@router.get("/trending/pins", response_model=TrendPinsResponse)
async def trending_pins(current_user: User = Depends(get_current_user)) -> TrendPinsResponse:
    return TrendPinsResponse(pins=list_trend_pins())


@router.post("/admin/trending/run", response_model=TrendRunResponse)
async def admin_trending_run(
    request: TrendRunRequest,
    current_user: User = Depends(get_current_user),
) -> TrendRunResponse:
    _require_hr_admin(current_user)
    created, skipped = run_trending(window_minutes=request.window_minutes, threshold=request.threshold)
    return TrendRunResponse(created_pins=created, skipped_topics=skipped)


@router.post("/feedback", response_model=FeedbackResponse)
async def feedback(
    request: FeedbackCreate,
    current_user: User = Depends(get_current_user),
) -> FeedbackResponse:
    try:
        create_feedback(current_user, request)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return FeedbackResponse(ok=True)


@router.post(
    "/documents",
    response_model=DocumentIngestResult,
    openapi_extra={
        "requestBody": {
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/DocumentCreate"},
                },
                "multipart/form-data": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "content": {"type": "string"},
                            "visibility_roles": {"type": "array", "items": {"type": "string"}},
                            "department_ids": {"type": "array", "items": {"type": "string"}},
                        },
                        "required": ["title", "content"],
                    },
                },
            },
            "required": True,
        }
    },
)
async def ingest_document(
    request: DocumentCreate,
    current_user: User = Depends(get_current_user),
) -> DocumentIngestResult:
    _require_hr_admin(current_user)
    document, indexed_count, warnings = create_document(request)
    return DocumentIngestResult(document=document, indexed_chunk_count=indexed_count, warnings=warnings)


@router.post("/documents/upload", response_model=DocumentIngestResult)
async def ingest_document_upload(
    file: UploadFile = File(...),
    title: str | None = Form(default=None),
    visibility_roles: list[str] | None = Form(default=None),
    department_ids: list[str] | None = Form(default=None),
    current_user: User = Depends(get_current_user),
) -> DocumentIngestResult:
    _require_hr_admin(current_user)
    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File tải lên phải có tên file")
    try:
        document, indexed_count, warnings = create_document_from_upload(
            filename=file.filename,
            content=await file.read(),
            title=title,
            visibility_roles=visibility_roles,
            department_ids=department_ids,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except ImportError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
    return DocumentIngestResult(document=document, indexed_chunk_count=indexed_count, warnings=warnings)


@router.get("/documents", response_model=DocumentListResponse)
async def documents(
    status_filter: str | None = Query(default=None, alias="status"),
    current_user: User = Depends(get_current_user),
) -> DocumentListResponse:
    _require_hr_admin(current_user)
    return DocumentListResponse(documents=list_documents(status_filter))


@router.delete("/documents/{document_id}", response_model=DocumentIngestResult)
async def remove_document(
    document_id: str,
    current_user: User = Depends(get_current_user),
) -> DocumentIngestResult:
    _require_hr_admin(current_user)
    document = delete_document(document_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy tài liệu")
    return DocumentIngestResult(document=document, indexed_chunk_count=0, warnings=[])


@router.get("/status")
async def agent_status():
    """Check baseline agent status."""
    return {"status": "ready", "agent": "HR Helpdesk AI scaffold"}


def _require_hr_admin(user: User) -> None:
    if user.role != "hr_admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cần quyền HR admin")


def _record_and_return_chat(current_user: User, request: ChatRequest, response: ChatResponse) -> ChatResponse:
    record_chat_query(
        message_id=response.message_id,
        user_id=current_user.id,
        query=request.message,
        citations=response.citations,
    )
    return response


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
