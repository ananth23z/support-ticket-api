"""
app/models/enums.py
===================
WHAT:  The fixed lists of allowed values: user roles, ticket statuses, priorities.
WHY:   Using an Enum instead of free text means a typo like "Resloved" is rejected
       automatically. Both the database models AND the Pydantic schemas use these,
       so the allowed values are defined in exactly ONE place.

       `class Role(str, Enum)` -> the members are ALSO strings, so Role.ADMIN == "admin".
       That makes them easy to store in the DB and to send as JSON.

ASP.NET ANALOGY:  A C# `enum` used in both your entity and your DTOs.
"""

from enum import Enum


class Role(str, Enum):
    ADMIN = "admin"        # manages users, sees & assigns every ticket
    AGENT = "agent"        # works on tickets assigned to them
    CUSTOMER = "customer"  # raises tickets and sees only their own


class TicketStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


class TicketPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
