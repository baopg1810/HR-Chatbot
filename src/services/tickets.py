from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from src.models.schemas import EscalationCreate, Ticket, TicketPriority, TicketStatus, User


_TICKETS: dict[str, Ticket] = {}


def create_ticket(requester: User, payload: EscalationCreate) -> Ticket:
    now = datetime.now(timezone.utc).isoformat()
    ticket = Ticket(
        id=f"ticket-{uuid4()}",
        requester_id=requester.id,
        status="open",
        priority=payload.priority,
        reason=payload.reason,
        summary=_summarize(payload.message),
        assignee_id=None,
        created_at=now,
        updated_at=now,
    )
    _TICKETS[ticket.id] = ticket
    return ticket


def create_ticket_from_chat(
    requester: User,
    message: str,
    reason: str,
    priority: TicketPriority = "normal",
    session_id: str | None = None,
) -> Ticket:
    allowed_reason = reason if reason in {"no_source", "outside_scope", "sensitive", "user_requested", "low_confidence"} else "low_confidence"
    return create_ticket(
        requester,
        EscalationCreate(session_id=session_id, message=message, reason=allowed_reason, priority=priority),
    )


def list_tickets(status: TicketStatus | None = None, priority: TicketPriority | None = None) -> list[Ticket]:
    tickets = list(_TICKETS.values())
    if status is not None:
        tickets = [ticket for ticket in tickets if ticket.status == status]
    if priority is not None:
        tickets = [ticket for ticket in tickets if ticket.priority == priority]
    return sorted(tickets, key=lambda ticket: ticket.created_at, reverse=True)


def update_ticket(
    ticket_id: str,
    status: TicketStatus | None = None,
    assignee_id: str | None = None,
    internal_note: str | None = None,
) -> Ticket | None:
    ticket = _TICKETS.get(ticket_id)
    if ticket is None:
        return None
    updated = ticket.model_copy(
        update={
            "status": status or ticket.status,
            "assignee_id": assignee_id if assignee_id is not None else ticket.assignee_id,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    _TICKETS[ticket_id] = updated
    return updated


def reset_ticket_store() -> None:
    _TICKETS.clear()


def _summarize(message: str, max_len: int = 180) -> str:
    summary = " ".join(message.split())
    if len(summary) <= max_len:
        return summary
    return summary[: max_len - 3] + "..."
