"""
app/models/ticket.py
====================
WHAT:  The `tickets` database table.
WHY:   Holds every support ticket with the properties listed in the requirements:
       ID, title, description, status, priority, created by, assigned agent,
       created date, updated date.

RELATIONSHIPS:
    tickets.created_by_id      --> users.id   (the customer who raised it)  REQUIRED
    tickets.assigned_agent_id  --> users.id   (the agent working on it)     OPTIONAL

ASP.NET ANALOGY:
    An EF Core entity with two foreign keys to the same `User` table, configured
    with `.HasOne(t => t.CreatedBy)` and `.HasOne(t => t.AssignedAgent)`.
"""

from datetime import datetime

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import TicketPriority, TicketStatus
from app.models.user import utc_now


class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    status: Mapped[TicketStatus] = mapped_column(
        SAEnum(TicketStatus, values_callable=lambda e: [m.value for m in e]),
        default=TicketStatus.OPEN,  # every new ticket starts as "open"
        nullable=False,
        index=True,                 # we filter by status often -> index it
    )
    priority: Mapped[TicketPriority] = mapped_column(
        SAEnum(TicketPriority, values_callable=lambda e: [m.value for m in e]),
        default=TicketPriority.MEDIUM,
        nullable=False,
        index=True,
    )

    # ---- Foreign keys ----------------------------------------------------
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    # `int | None` + nullable=True -> a ticket may not be assigned yet.
    assigned_agent_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    # ---- Timestamps ------------------------------------------------------
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    # `onupdate=utc_now` -> SQLAlchemy automatically refreshes this on every UPDATE.
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    # ---- Navigation properties -------------------------------------------
    # Lets us write `ticket.created_by.email` instead of doing a manual lookup.
    created_by: Mapped["User"] = relationship(  # noqa: F821
        back_populates="created_tickets", foreign_keys=[created_by_id]
    )
    assigned_agent: Mapped["User | None"] = relationship(  # noqa: F821
        back_populates="assigned_tickets", foreign_keys=[assigned_agent_id]
    )

    def __repr__(self) -> str:
        return f"<Ticket id={self.id} title={self.title!r} status={self.status}>"
