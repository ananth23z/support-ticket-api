"""
app/services/ticket_service.py
==============================
WHAT:  All ticket business rules: who can see/change what, search, filter,
       sort, paginate, assign, change status, statistics.
WHY:   This is the "brain" of the application. Routers only call these functions.

PERMISSION RULES (summary):
    | Action            | Customer              | Agent                  | Admin |
    |-------------------|-----------------------|------------------------|-------|
    | Create ticket     | yes                   | no                     | no    |
    | List / view       | own tickets only      | tickets assigned to me | all   |
    | Edit title/desc   | own ticket, if OPEN   | no                     | yes   |
    | Change status     | no                    | my tickets (not CLOSED)| yes   |
    | Assign to agent   | no                    | no                     | yes   |
    | Delete            | no                    | no                     | yes   |

    Coarse role checks ("is admin?") happen in the router via require_roles().
    Fine-grained checks ("is this MY ticket?") need the ticket data, so they happen here.
"""

import logging
import math

from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestError, ForbiddenError, NotFoundError
from app.models import Role, Ticket, TicketPriority, TicketStatus, User
from app.schemas.ticket import TicketCreate, TicketUpdate

logger = logging.getLogger("app.tickets")


# ---------------------------------------------------------------------------
# Small private helpers (the leading underscore means "internal to this file")
# ---------------------------------------------------------------------------
def _can_view(user: User, ticket: Ticket) -> bool:
    if user.role == Role.ADMIN:
        return True
    if user.role == Role.AGENT:
        return ticket.assigned_agent_id == user.id
    return ticket.created_by_id == user.id  # customer


def _get_ticket_or_404(db: Session, ticket_id: int) -> Ticket:
    ticket = db.get(Ticket, ticket_id)
    if ticket is None:
        raise NotFoundError(f"Ticket {ticket_id} not found")
    return ticket


# ---------------------------------------------------------------------------
# CREATE
# ---------------------------------------------------------------------------
def create_ticket(db: Session, data: TicketCreate, customer: User) -> Ticket:
    ticket = Ticket(
        title=data.title,
        description=data.description,
        priority=data.priority,
        created_by_id=customer.id,  # the owner is ALWAYS the logged-in user (never from the body)
        # status defaults to OPEN, assigned_agent_id defaults to None (see the model)
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    logger.info("Ticket %s created by user %s", ticket.id, customer.id)
    return ticket


# ---------------------------------------------------------------------------
# READ (one)
# ---------------------------------------------------------------------------
def get_ticket(db: Session, ticket_id: int, user: User) -> Ticket:
    ticket = _get_ticket_or_404(db, ticket_id)
    if not _can_view(user, ticket):
        raise ForbiddenError("You do not have access to this ticket")
    return ticket


# ---------------------------------------------------------------------------
# READ (many) - search + filter + sort + pagination
# ---------------------------------------------------------------------------
# To sort by priority we can't sort alphabetically ("critical" < "high" < "low"...).
# `case(...)` turns each priority into a number the database can sort by:
#   low=1, medium=2, high=3, critical=4
PRIORITY_ORDER = case(
    {
        TicketPriority.LOW: 1,
        TicketPriority.MEDIUM: 2,
        TicketPriority.HIGH: 3,
        TicketPriority.CRITICAL: 4,
    },
    value=Ticket.priority,
)


def list_tickets(
    db: Session,
    user: User,
    search: str | None = None,
    status: TicketStatus | None = None,
    priority: TicketPriority | None = None,
    sort_by: str = "created_at",
    order: str = "desc",
    page: int = 1,
    size: int = 10,
) -> dict:
    """
    Builds ONE SQL query step by step. Nothing is sent to the DB until we
    call db.execute(). This is like building an IQueryable in LINQ and then
    calling .ToList() at the end.
    """
    query = select(Ticket)

    # 1) SCOPE: what is this user allowed to see at all?
    if user.role == Role.AGENT:
        query = query.where(Ticket.assigned_agent_id == user.id)
    elif user.role == Role.CUSTOMER:
        query = query.where(Ticket.created_by_id == user.id)
    # admin: no restriction

    # 2) SEARCH: title OR description contains the text (case-insensitive).
    #    .ilike("%abc%") -> SQL:  title LIKE '%abc%'  (i = ignore case)
    if search:
        pattern = f"%{search}%"
        query = query.where(or_(Ticket.title.ilike(pattern), Ticket.description.ilike(pattern)))

    # 3) FILTERS
    if status is not None:
        query = query.where(Ticket.status == status)
    if priority is not None:
        query = query.where(Ticket.priority == priority)

    # 4) COUNT the total BEFORE pagination, so the client knows how many pages exist.
    #    SELECT COUNT(*) FROM (<our query>)
    total = db.execute(select(func.count()).select_from(query.subquery())).scalar_one()

    # 5) SORT
    sort_column = PRIORITY_ORDER if sort_by == "priority" else Ticket.created_at
    sort_expression = sort_column.asc() if order == "asc" else sort_column.desc()
    # add id as a tie-breaker so the order is always stable between pages
    query = query.order_by(sort_expression, Ticket.id.desc())

    # 6) PAGINATE: page 1 -> skip 0, page 2 -> skip `size`, ...
    #    SQL:  LIMIT size OFFSET (page-1)*size
    query = query.offset((page - 1) * size).limit(size)

    items = list(db.execute(query).scalars().all())
    return {
        "items": items,
        "total": total,
        "page": page,
        "size": size,
        "pages": math.ceil(total / size) if total else 0,
    }


# ---------------------------------------------------------------------------
# UPDATE (title / description / priority)
# ---------------------------------------------------------------------------
def update_ticket(db: Session, ticket_id: int, data: TicketUpdate, user: User) -> Ticket:
    ticket = _get_ticket_or_404(db, ticket_id)

    if user.role == Role.CUSTOMER:
        if ticket.created_by_id != user.id:
            raise ForbiddenError("You can only edit your own tickets")
        if ticket.status != TicketStatus.OPEN:
            raise BadRequestError("You can only edit a ticket while it is still open")
    elif user.role != Role.ADMIN:
        raise ForbiddenError("Agents cannot edit ticket details; update the status instead")

    # model_dump(exclude_unset=True) gives ONLY the fields the client actually sent.
    # e.g. body {"priority": "high"} -> {"priority": "high"}  (title/description untouched)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(ticket, field, value)  # same as ticket.priority = "high"

    db.commit()
    db.refresh(ticket)
    return ticket


# ---------------------------------------------------------------------------
# UPDATE STATUS
# ---------------------------------------------------------------------------
def update_status(db: Session, ticket_id: int, new_status: TicketStatus, user: User) -> Ticket:
    ticket = _get_ticket_or_404(db, ticket_id)

    if user.role == Role.AGENT:
        if ticket.assigned_agent_id != user.id:
            raise ForbiddenError("You can only update tickets assigned to you")
        if ticket.status == TicketStatus.CLOSED:
            raise BadRequestError("Closed tickets cannot be changed (ask an admin to reopen)")

    old_status = ticket.status
    ticket.status = new_status
    db.commit()
    db.refresh(ticket)
    logger.info("Ticket %s status %s -> %s by user %s", ticket.id, old_status.value, new_status.value, user.id)
    return ticket


# ---------------------------------------------------------------------------
# ASSIGN (admin)
# ---------------------------------------------------------------------------
def assign_ticket(db: Session, ticket_id: int, agent_id: int) -> Ticket:
    ticket = _get_ticket_or_404(db, ticket_id)

    agent = db.get(User, agent_id)
    if agent is None:
        raise NotFoundError(f"User {agent_id} not found")
    if agent.role != Role.AGENT:
        raise BadRequestError("Tickets can only be assigned to users with the 'agent' role")
    if not agent.is_active:
        raise BadRequestError("Cannot assign a ticket to an inactive agent")

    ticket.assigned_agent_id = agent.id
    db.commit()
    db.refresh(ticket)
    logger.info("Ticket %s assigned to agent %s", ticket.id, agent.id)
    return ticket


# ---------------------------------------------------------------------------
# DELETE (admin)
# ---------------------------------------------------------------------------
def delete_ticket(db: Session, ticket_id: int) -> None:
    ticket = _get_ticket_or_404(db, ticket_id)
    db.delete(ticket)
    db.commit()
    logger.info("Ticket %s deleted", ticket_id)


# ---------------------------------------------------------------------------
# STATS (admin monitoring)
# ---------------------------------------------------------------------------
def get_stats(db: Session) -> dict:
    """
    GROUP BY queries:  SELECT status, COUNT(*) FROM tickets GROUP BY status
    We start every status/priority at 0 so missing ones still appear in the result.
    """
    by_status = {s.value: 0 for s in TicketStatus}
    for status_value, count in db.execute(select(Ticket.status, func.count()).group_by(Ticket.status)):
        by_status[status_value.value] = count

    by_priority = {p.value: 0 for p in TicketPriority}
    for priority_value, count in db.execute(select(Ticket.priority, func.count()).group_by(Ticket.priority)):
        by_priority[priority_value.value] = count

    unassigned = db.execute(
        select(func.count()).select_from(Ticket).where(Ticket.assigned_agent_id.is_(None))
    ).scalar_one()

    return {
        "total": sum(by_status.values()),
        "by_status": by_status,
        "by_priority": by_priority,
        "unassigned": unassigned,
    }
