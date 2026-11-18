"""
app/routers/tickets.py
======================
WHAT:  All ticket endpoints.
WHY:   Exposes ticket_service over HTTP. Notice there are NO business rules here -
       only: read the request -> call the service -> return the result.

QUERY PARAMETERS with validation:
    page: int = Query(1, ge=1)  -> ?page=2 ; must be >= 1 (ge = "greater or equal")
    size: int = Query(10, ge=1, le=100) -> max 100 per page (protects the server)
    Literal["created_at", "priority"] -> only these exact strings are accepted.

ROUTE ORDER MATTERS:
    `/stats` is declared BEFORE `/{ticket_id}`. Otherwise FastAPI would try to read
    "stats" as a ticket_id, fail int conversion, and return 422.
"""

from typing import Literal

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, get_db, require_roles
from app.models import Role, TicketPriority, TicketStatus, User
from app.schemas.ticket import (
    PaginatedTickets,
    TicketAssign,
    TicketCreate,
    TicketResponse,
    TicketStats,
    TicketStatusUpdate,
    TicketUpdate,
)
from app.services import ticket_service

router = APIRouter(prefix="/tickets", tags=["Tickets"])


@router.post("", response_model=TicketResponse, status_code=status.HTTP_201_CREATED)
def create_ticket(
    data: TicketCreate,
    current_user: User = Depends(require_roles(Role.CUSTOMER)),  # customers only
    db: Session = Depends(get_db),
):
    """Raise a new support ticket (**customer** only)."""
    return ticket_service.create_ticket(db, data, current_user)


@router.get("", response_model=PaginatedTickets)
def list_tickets(
    search: str | None = Query(None, max_length=100, description="Text to find in title or description"),
    status_filter: TicketStatus | None = Query(None, alias="status", description="Filter by status"),
    priority: TicketPriority | None = Query(None, description="Filter by priority"),
    sort_by: Literal["created_at", "priority"] = Query("created_at"),
    order: Literal["asc", "desc"] = Query("desc"),
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List tickets **you are allowed to see**:
    customers -> their own, agents -> assigned to them, admins -> all.

    Example: `/tickets?search=login&status=open&priority=high&sort_by=priority&page=1&size=5`
    """
    # Note: we call the Python variable `status_filter` (with alias="status" for the URL)
    # because `status` is already the name of the imported fastapi.status module.
    return ticket_service.list_tickets(
        db, current_user,
        search=search, status=status_filter, priority=priority,
        sort_by=sort_by, order=order, page=page, size=size,
    )


@router.get("/stats", response_model=TicketStats, dependencies=[Depends(require_roles(Role.ADMIN))])
def ticket_stats(db: Session = Depends(get_db)):
    """Counts by status and priority, for monitoring (**admin** only)."""
    return ticket_service.get_stats(db)


@router.get("/{ticket_id}", response_model=TicketResponse)
def get_ticket(ticket_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get one ticket (only if you are allowed to see it)."""
    return ticket_service.get_ticket(db, ticket_id, current_user)


@router.put("/{ticket_id}", response_model=TicketResponse)
def update_ticket(
    ticket_id: int,
    data: TicketUpdate,
    current_user: User = Depends(require_roles(Role.CUSTOMER, Role.ADMIN)),
    db: Session = Depends(get_db),
):
    """Edit title/description/priority. Customers: own tickets while still open. Admins: any."""
    return ticket_service.update_ticket(db, ticket_id, data, current_user)


@router.patch("/{ticket_id}/status", response_model=TicketResponse)
def update_ticket_status(
    ticket_id: int,
    data: TicketStatusUpdate,
    current_user: User = Depends(require_roles(Role.AGENT, Role.ADMIN)),
    db: Session = Depends(get_db),
):
    """Change status (**agent** on their assigned tickets, or **admin**)."""
    return ticket_service.update_status(db, ticket_id, data.status, current_user)


@router.patch(
    "/{ticket_id}/assign",
    response_model=TicketResponse,
    dependencies=[Depends(require_roles(Role.ADMIN))],
)
def assign_ticket(ticket_id: int, data: TicketAssign, db: Session = Depends(get_db)):
    """Assign a ticket to an agent (**admin** only)."""
    return ticket_service.assign_ticket(db, ticket_id, data.agent_id)


@router.delete(
    "/{ticket_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_roles(Role.ADMIN))],
)
def delete_ticket(ticket_id: int, db: Session = Depends(get_db)):
    """Delete a ticket (**admin** only). Returns 204 No Content (empty body)."""
    ticket_service.delete_ticket(db, ticket_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
