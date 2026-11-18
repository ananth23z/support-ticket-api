"""
app/services/user_service.py
============================
WHAT:  Business logic for users: create, find, list, update.
WHY:   The SERVICE LAYER keeps rules in one place, separate from HTTP.
         - Routers  : "translate HTTP <-> Python" (thin, no rules)
         - Services : "what is allowed and what happens" (rules live here)
         - Models   : "how data is stored"
       Because services don't know about HTTP, they're easy to test and reuse
       (e.g. main.py reuses create_user to seed the first admin).

ASP.NET ANALOGY:
    A `UserService : IUserService` class injected into a controller.
    Python doesn't need interfaces/classes for this - plain functions that
    receive the `db` session as a parameter work great and are simpler.

PATTERN USED IN EVERY FUNCTION:
    def something(db: Session, ...):
        ... query or modify objects ...
        db.commit()          # save changes (like SaveChanges() in EF)
        db.refresh(obj)      # reload fields the DB generated (id, timestamps)
        return obj
"""

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.core.security import hash_password
from app.models import Role, User
from app.schemas.user import UserAdminUpdate, UserUpdate

logger = logging.getLogger("app.users")


def get_user_by_email(db: Session, email: str) -> User | None:
    # select(User).where(...) builds:  SELECT * FROM users WHERE email = :email
    # .scalar_one_or_none() -> returns one User object, or None if no row.
    return db.execute(select(User).where(User.email == email.lower())).scalar_one_or_none()


def get_user_by_id(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise NotFoundError(f"User {user_id} not found")
    return user


def create_user(db: Session, email: str, full_name: str, password: str, role: Role = Role.CUSTOMER) -> User:
    """Create a user after checking the email is free. Password is hashed here."""
    if get_user_by_email(db, email):
        raise ConflictError("A user with this email already exists")  # -> HTTP 409

    user = User(
        email=email.lower(),  # store emails lower-case so "A@x.com" == "a@x.com"
        full_name=full_name,
        hashed_password=hash_password(password),  # NEVER store the plain password
        role=role,
    )
    db.add(user)      # stage the INSERT
    db.commit()       # run it
    db.refresh(user)  # now user.id and user.created_at are filled in
    logger.info("Created user id=%s email=%s role=%s", user.id, user.email, user.role.value)
    return user


def list_users(db: Session, role: Role | None = None) -> list[User]:
    query = select(User).order_by(User.id)
    if role is not None:  # optional filter: ?role=agent
        query = query.where(User.role == role)
    return list(db.execute(query).scalars().all())


def update_own_profile(db: Session, user: User, data: UserUpdate) -> User:
    """A user edits their own name and/or password."""
    if data.full_name is not None:
        user.full_name = data.full_name
    if data.password is not None:
        user.hashed_password = hash_password(data.password)
    # No db.add() needed: `user` was loaded from this session, so SQLAlchemy
    # is already tracking it and notices the changes (EF "change tracking").
    db.commit()
    db.refresh(user)
    return user


def admin_update_user(db: Session, user_id: int, data: UserAdminUpdate) -> User:
    """Admin changes someone's role or active flag."""
    user = get_user_by_id(db, user_id)
    if data.role is not None:
        user.role = data.role
    if data.is_active is not None:
        user.is_active = data.is_active
    db.commit()
    db.refresh(user)
    logger.info("Admin updated user id=%s -> role=%s active=%s", user.id, user.role.value, user.is_active)
    return user


def ensure_default_admin(db: Session, email: str, password: str) -> None:
    """
    Called once at startup (main.py). If no admin exists yet, create one,
    otherwise nobody could ever log in as admin to create agents.
    """
    admin_exists = db.execute(select(User).where(User.role == Role.ADMIN)).first()
    if admin_exists:
        return
    create_user(db, email=email, full_name="System Admin", password=password, role=Role.ADMIN)
    logger.warning("Default admin created: %s  (change this password!)", email)
