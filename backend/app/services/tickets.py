from __future__ import annotations

import uuid
from typing import Any

from app.models.schemas import EscalationCreate, Ticket, TicketPriority, TicketStatus, User
from app.database.session import get_db_context
from app.models.ticket import Ticket as DBTicket

EMPLOYEE_MOCK_ID = "emp-001"
EMPLOYEE_UUID = uuid.UUID("00000000-0000-0000-0000-000000000001")

ADMIN_MOCK_ID = "hr-001"
ADMIN_UUID = uuid.UUID("00000000-0000-0000-0000-000000000002")

def safe_parse_uuid(val: Any) -> uuid.UUID | None:
    if not val:
        return None
    if isinstance(val, uuid.UUID):
        return val
    val_str = str(val).strip()
    if val_str == EMPLOYEE_MOCK_ID:
        return EMPLOYEE_UUID
    if val_str == ADMIN_MOCK_ID:
        return ADMIN_UUID
    cleaned = val_str.replace("session-", "").replace("ticket-", "").replace("usr-", "").replace("user-", "").replace("msg-", "")
    try:
        return uuid.UUID(cleaned)
    except ValueError:
        return uuid.uuid5(uuid.NAMESPACE_DNS, cleaned)

def map_uuid_to_mock_id(u: uuid.UUID | str | None) -> str | None:
    if not u:
        return None
    u_str = str(u).strip()
    if u_str == str(EMPLOYEE_UUID):
        return EMPLOYEE_MOCK_ID
    if u_str == str(ADMIN_UUID):
        return ADMIN_MOCK_ID
    return u_str

def map_db_to_pydantic_ticket(db_ticket: DBTicket) -> Ticket:
    # Map database priority (medium/low/high) to Pydantic priority (normal/low/high)
    priority = "normal" if db_ticket.priority == "medium" else db_ticket.priority
    return Ticket(
        id=f"ticket-{db_ticket.id}",
        requester_id=map_uuid_to_mock_id(db_ticket.user_id) or str(db_ticket.user_id),
        status=db_ticket.status,
        priority=priority,
        reason=db_ticket.question,
        summary=_summarize(db_ticket.question),
        assignee_id=map_uuid_to_mock_id(db_ticket.assigned_to) or (str(db_ticket.assigned_to) if db_ticket.assigned_to else None),
        created_at=db_ticket.created_at.isoformat() if hasattr(db_ticket.created_at, "isoformat") else str(db_ticket.created_at),
        updated_at=db_ticket.updated_at.isoformat() if hasattr(db_ticket.updated_at, "isoformat") else str(db_ticket.updated_at),
    )

async def create_ticket(requester: User, payload: EscalationCreate, db: Any = None) -> Ticket:
    user_uuid = safe_parse_uuid(requester.id)
    if not user_uuid:
        # Fallback to a seeded admin user or similar if requester.id is not a valid UUID format
        # During testing, mock users can have ids like "emp-001".
        # Let's resolve to first user ID in DB if not parseable
        from sqlalchemy import select
        from app.models.user import User as DBUser
        async with get_db_context() as session:
            res = await session.execute(select(DBUser.id).limit(1))
            first_user_id = res.scalar()
            if first_user_id:
                user_uuid = first_user_id
            else:
                user_uuid = uuid.uuid4() # Mock fallback

    session_uuid = safe_parse_uuid(payload.session_id)
    if session_uuid and user_uuid:
        from app.models.chat import ChatSession
        if db is not None:
            db_session = await db.get(ChatSession, session_uuid)
            if not db_session:
                db_session = ChatSession(id=session_uuid, user_id=user_uuid, title="Chat Session")
                db.add(db_session)
                await db.flush()
        else:
            async with get_db_context() as session:
                db_session = await session.get(ChatSession, session_uuid)
                if not db_session:
                    db_session = ChatSession(id=session_uuid, user_id=user_uuid, title="Chat Session")
                    session.add(db_session)
                    await session.commit()

    db_ticket = DBTicket(
        user_id=user_uuid,
        session_id=session_uuid,
        question=payload.message,
        status="open",
        priority="medium" if payload.priority == "normal" else payload.priority,
        assigned_to=None
    )

    if db is not None:
        db.add(db_ticket)
        await db.commit()
        await db.refresh(db_ticket)
    else:
        async with get_db_context() as session:
            session.add(db_ticket)
            await session.commit()
            await session.refresh(db_ticket)

    return map_db_to_pydantic_ticket(db_ticket)

async def create_ticket_from_chat(
    requester: User,
    message: str,
    reason: str,
    priority: TicketPriority = "normal",
    session_id: str | None = None,
    db: Any = None
) -> Ticket:
    allowed_reason = reason if reason in {"no_source", "outside_scope", "sensitive", "user_requested", "low_confidence"} else "low_confidence"
    return await create_ticket(
        requester,
        EscalationCreate(session_id=session_id, message=message, reason=allowed_reason, priority=priority),
        db=db
    )

async def list_tickets(
    status: TicketStatus | None = None,
    priority: TicketPriority | None = None,
    requester_id: str | None = None,
    db: Any = None,
) -> list[Ticket]:
    from sqlalchemy import select
    stmt = select(DBTicket)
    if status is not None:
        stmt = stmt.filter(DBTicket.status == status)
    if priority is not None:
        db_priority = "medium" if priority == "normal" else priority
        stmt = stmt.filter(DBTicket.priority == db_priority)
    if requester_id is not None:
        requester_uuid = safe_parse_uuid(requester_id)
        if requester_uuid is None:
            return []
        stmt = stmt.filter(DBTicket.user_id == requester_uuid)
    stmt = stmt.order_by(DBTicket.created_at.desc())

    if db is not None:
        res = await db.execute(stmt)
        db_tickets = res.scalars().all()
    else:
        async with get_db_context() as session:
            res = await session.execute(stmt)
            db_tickets = res.scalars().all()

    return [map_db_to_pydantic_ticket(t) for t in db_tickets]

async def update_ticket(
    ticket_id: str,
    status: TicketStatus | None = None,
    assignee_id: str | None = None,
    internal_note: str | None = None,
    db: Any = None
) -> Ticket | None:
    ticket_uuid = safe_parse_uuid(ticket_id)
    if not ticket_uuid:
        return None

    if db is not None:
        db_ticket = await db.get(DBTicket, ticket_uuid)
        if not db_ticket:
            return None
        if status is not None:
            db_ticket.status = status
        if assignee_id is not None:
            db_ticket.assigned_to = safe_parse_uuid(assignee_id)
        await db.commit()
        await db.refresh(db_ticket)
    else:
        async with get_db_context() as session:
            db_ticket = await session.get(DBTicket, ticket_uuid)
            if not db_ticket:
                return None
            if status is not None:
                db_ticket.status = status
            if assignee_id is not None:
                db_ticket.assigned_to = safe_parse_uuid(assignee_id)
            session.add(db_ticket)
            await session.commit()
            await session.refresh(db_ticket)

    return map_db_to_pydantic_ticket(db_ticket)

def reset_ticket_store() -> None:
    pass

def _summarize(message: str, max_len: int = 180) -> str:
    summary = " ".join(message.split())
    if len(summary) <= max_len:
        return summary
    return summary[: max_len - 3] + "..."

