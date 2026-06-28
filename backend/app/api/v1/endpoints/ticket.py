from fastapi import APIRouter, Depends, HTTPException, Query, status
from app.schemas.schemas import EscalationCreate, Ticket, TicketListResponse, TicketUpdate, TicketStatus, TicketPriority
from app.api.deps import get_current_user
from app.models.user import User
from app.services.tickets import create_ticket, list_tickets, update_ticket

router = APIRouter()

def _require_hr_admin(user: User) -> None:
    if user.role != "hr_admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cần quyền HR admin")

@router.post("/escalations", response_model=Ticket)
async def create_escalation(
    request: EscalationCreate,
    current_user: User = Depends(get_current_user),
) -> Ticket:
    return await create_ticket(current_user, request)

@router.get("/tickets", response_model=TicketListResponse)
async def my_tickets(
    status_filter: TicketStatus | None = Query(default=None, alias="status"),
    priority: TicketPriority | None = Query(default=None),
    current_user: User = Depends(get_current_user),
) -> TicketListResponse:
    return TicketListResponse(
        tickets=await list_tickets(
            status=status_filter,
            priority=priority,
            requester_id=current_user.id,
        )
    )

@router.get("/admin/tickets", response_model=TicketListResponse)
async def admin_tickets(
    status_filter: TicketStatus | None = Query(default=None, alias="status"),
    priority: TicketPriority | None = Query(default=None),
    current_user: User = Depends(get_current_user),
) -> TicketListResponse:
    _require_hr_admin(current_user)
    return TicketListResponse(tickets=await list_tickets(status=status_filter, priority=priority))

@router.patch("/admin/tickets/{ticket_id}", response_model=Ticket)
async def patch_ticket(
    ticket_id: str,
    request: TicketUpdate,
    current_user: User = Depends(get_current_user),
) -> Ticket:
    _require_hr_admin(current_user)
    ticket = await update_ticket(
        ticket_id,
        status=request.status,
        assignee_id=request.assignee_id,
        internal_note=request.internal_note,
    )
    if ticket is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy ticket")
    return ticket

