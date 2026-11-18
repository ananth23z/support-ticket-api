"""
app/models/user.py
==================
WHAT:  The `users` database table, described as a Python class (an ORM "model").
WHY:   With an ORM (Object Relational Mapper) we work with Python objects
       (`user.email`) instead of writing SQL by hand. SQLAlchemy translates
       between the two.

ASP.NET ANALOGY:
    This is an Entity Framework entity class, e.g. `public class User { ... }`,
    and `relationship(...)` is like a navigation property
    (`public ICollection<Ticket> CreatedTickets { get; set; }`).

IMPORTANT DIFFERENCE: MODEL vs SCHEMA
    - Model (this file)   = what is stored in the DATABASE (includes hashed_password!)
    - Schema (schemas/)   = what goes IN/OUT of the API as JSON (never exposes the hash)
"""

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum as SAEnum, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import Role


def utc_now() -> datetime:
    """Current time in UTC. Always store UTC in databases; convert to local time in the UI."""
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"  # the actual table name in the database

    # `Mapped[int]` is the Python type; `mapped_column(...)` describes the DB column.
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # unique=True -> the DB itself refuses two users with the same email.
    # index=True  -> makes "find user by email" (used at login) fast.
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)

    # We store the HASH, never the password itself. (See core/security.py)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)

    # SAEnum stores the enum value ("admin"/"agent"/"customer") as text.
    role: Mapped[Role] = mapped_column(
        SAEnum(Role, values_callable=lambda e: [m.value for m in e]),
        default=Role.CUSTOMER,
        nullable=False,
    )

    # Instead of deleting users we can deactivate them (they can no longer log in).
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    # ---- Relationships (navigation properties) ---------------------------
    # A user can CREATE many tickets (as a customer) ...
    # The string "Ticket" is used (not the class) to avoid circular imports.
    # `foreign_keys=` is needed because Ticket has TWO foreign keys to users
    # (created_by_id and assigned_agent_id) so SQLAlchemy must know which one.
    created_tickets: Mapped[list["Ticket"]] = relationship(  # noqa: F821
        back_populates="created_by", foreign_keys="Ticket.created_by_id"
    )
    # ... and can be ASSIGNED many tickets (as an agent).
    assigned_tickets: Mapped[list["Ticket"]] = relationship(  # noqa: F821
        back_populates="assigned_agent", foreign_keys="Ticket.assigned_agent_id"
    )

    def __repr__(self) -> str:  # nice text when you print(user) while debugging
        return f"<User id={self.id} email={self.email} role={self.role}>"
