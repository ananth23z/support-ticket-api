"""
app/schemas/ticket.py
=====================
WHAT:  Request/response schemas for tickets, plus the paginated list wrapper.
WHY:   Each endpoint accepts ONLY the fields that make sense for it:
         - a customer creating a ticket can't set `status` or `assigned_agent_id`
         - changing status uses its own tiny schema (TicketStatusUpdate)
         - assigning uses TicketAssign
       This is safer than one big "Ticket" schema where a customer could sneak
       `"status": "closed"` into the request. (This attack is called "over-posting"
       / "mass assignment" - the same thing ASP.NET warns about with [Bind].)
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import TicketPriority, TicketStatus
from app.schemas.user import UserSummary


class TicketCreate(BaseModel):
    """Body for POST /tickets (customer raises a ticket)."""

    title: str = Field(min_length=3, max_length=200, examples=["Cannot log in to the portal"])
    description: str = Field(min_length=10, max_length=5000, examples=["Since this morning I get 'invalid password'..."])
    priority: TicketPriority = TicketPriority.MEDIUM  # optional; defaults to medium


class TicketUpdate(BaseModel):
    """Body for PUT /tickets/{id} - edit text/priority. All fields optional."""

    title: str | None = Field(default=None, min_length=3, max_length=200)
    description: str | None = Field(default=None, min_length=10, max_length=5000)
    priority: TicketPriority | None = None


class TicketStatusUpdate(BaseModel):
    """Body for PATCH /tickets/{id}/status."""

    status: TicketStatus


class TicketAssign(BaseModel):
    """Body for PATCH /tickets/{id}/assign (admin only)."""

    agent_id: int = Field(gt=0)  # gt=0 -> "greater than 0"


class TicketResponse(BaseModel):
    """What the API returns for one ticket."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str
    status: TicketStatus
    priority: TicketPriority
    # These are filled from the ORM relationships ticket.created_by / ticket.assigned_agent
    created_by: UserSummary
    assigned_agent: UserSummary | None
    created_at: datetime
    updated_at: datetime


class PaginatedTickets(BaseModel):
    """
    Wrapper for list endpoints. Returning a plain list gives the client no idea
    how many results exist in total, so we also send paging information.
    """

    items: list[TicketResponse]
    total: int  # how many tickets match the filters (across ALL pages)
    page: int   # current page number (starts at 1)
    size: int   # items per page
    pages: int  # total number of pages


class TicketStats(BaseModel):
    """Simple numbers for the admin dashboard (GET /tickets/stats)."""

    total: int
    by_status: dict[str, int]
    by_priority: dict[str, int]
    unassigned: int
