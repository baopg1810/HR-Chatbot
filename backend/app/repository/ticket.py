from app.repository.base import BaseRepository
from app.models.ticket import Ticket

class TicketRepository(BaseRepository[Ticket]):
    pass

ticket_repository = TicketRepository(Ticket)
