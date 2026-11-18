"""
app/schemas/user.py
===================
WHAT:  Pydantic "schemas" describing the JSON that goes IN and OUT of user endpoints.
WHY:   1. VALIDATION  - FastAPI checks incoming JSON against these classes BEFORE your
                        code runs. Bad data -> automatic 422 error with a clear message.
       2. SECURITY    - Response schemas decide which fields leave the server.
                        `UserResponse` has no `hashed_password`, so it can never leak.
       3. DOCUMENTATION - Swagger UI (/docs) is generated from these classes.

ASP.NET ANALOGY:
    These are DTOs (Data Transfer Objects) / ViewModels with DataAnnotations like
    [Required], [EmailAddress], [StringLength(100, MinimumLength = 2)].
    `Field(min_length=2)` is Pydantic's version of `[StringLength]`.

NAMING CONVENTION used in this project:
    XxxCreate   -> body for creating something       (POST)
    XxxUpdate   -> body for changing something       (PUT/PATCH) - fields optional
    XxxResponse -> what the API sends back
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.enums import Role


class UserRegister(BaseModel):
    """Body for POST /auth/register (public sign-up -> always becomes a CUSTOMER)."""

    email: EmailStr  # EmailStr validates the format, e.g. rejects "not-an-email"
    full_name: str = Field(min_length=2, max_length=100, examples=["Jane Customer"])
    password: str = Field(min_length=8, max_length=128, examples=["Secret123!"])


class UserCreateByAdmin(UserRegister):
    """
    Body for POST /users (ADMIN only). Inherits email/full_name/password from
    UserRegister and ADDS `role`, so an admin can create agents or other admins.
    """

    role: Role = Role.CUSTOMER


class UserUpdate(BaseModel):
    """
    Body for PUT /users/me. Every field is OPTIONAL (`| None = None`):
    the user sends only what they want to change.
    """

    full_name: str | None = Field(default=None, min_length=2, max_length=100)
    password: str | None = Field(default=None, min_length=8, max_length=128)


class UserAdminUpdate(BaseModel):
    """Body for PATCH /users/{id} (ADMIN only): change someone's role or deactivate them."""

    role: Role | None = None
    is_active: bool | None = None


class UserResponse(BaseModel):
    """What we send back for a user. Notice: NO password/hash field here."""

    # from_attributes=True lets Pydantic read data from a SQLAlchemy object
    # (user.email) instead of only from a dict (user["email"]).
    # ASP.NET analogy: AutoMapper mapping Entity -> DTO, but automatic.
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    full_name: str
    role: Role
    is_active: bool
    created_at: datetime


class UserSummary(BaseModel):
    """A small version of a user, embedded inside ticket responses."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    email: EmailStr
