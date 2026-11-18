"""
app/models package
==================
Importing every model HERE guarantees they are all registered on `Base.metadata`
before `Base.metadata.create_all()` runs in main.py. If a model is never imported,
SQLAlchemy doesn't know it exists and its table won't be created.

Other files can now simply do:  from app.models import User, Ticket, Role
"""

from app.models.enums import Role, TicketPriority, TicketStatus
from app.models.user import User
from app.models.ticket import Ticket

__all__ = ["Role", "TicketPriority", "TicketStatus", "User", "Ticket"]
