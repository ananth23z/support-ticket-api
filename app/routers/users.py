"""
app/routers/users.py
====================
WHAT:  Profile endpoints (any logged-in user) + user management (admin only).

TWO WAYS TO PROTECT AN ENDPOINT:
  1) As a parameter - when you NEED the user object inside the function:
        def me(current_user: User = Depends(get_current_user)):
  2) In `dependencies=[...]` - when you only need the CHECK, not the object:
        @router.get("", dependencies=[Depends(require_roles(Role.ADMIN))])
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, get_db, require_roles
from app.models import Role, User
from app.schemas.user import UserAdminUpdate, UserCreateByAdmin, UserResponse, UserUpdate
from app.services import user_service

router = APIRouter(prefix="/users", tags=["Users"])

# A reusable "admin only" dependency, so we don't repeat require_roles(Role.ADMIN).
admin_only = Depends(require_roles(Role.ADMIN))


# ---------------------------------------------------------------------------
# PROFILE - any logged-in user
# ---------------------------------------------------------------------------
@router.get("/me", response_model=UserResponse)
def read_my_profile(current_user: User = Depends(get_current_user)):
    """Return the profile of whoever owns the token."""
    return current_user  # FastAPI converts the ORM object -> UserResponse JSON


@router.put("/me", response_model=UserResponse)
def update_my_profile(
    data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Change your own name and/or password."""
    return user_service.update_own_profile(db, current_user, data)


# ---------------------------------------------------------------------------
# ADMINISTRATION - admin only
# ---------------------------------------------------------------------------
@router.get("", response_model=list[UserResponse], dependencies=[admin_only])
def list_users(role: Role | None = None, db: Session = Depends(get_db)):
    """
    List all users. Optional filter: `?role=agent`.
    `role` is not in the path and not a Pydantic body, so FastAPI treats it as a
    QUERY PARAMETER automatically (like [FromQuery] in ASP.NET).
    """
    return user_service.list_users(db, role)


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED, dependencies=[admin_only])
def create_user(data: UserCreateByAdmin, db: Session = Depends(get_db)):
    """Create a user with any role - this is how admins create **agents**."""
    return user_service.create_user(
        db, email=data.email, full_name=data.full_name, password=data.password, role=data.role
    )


@router.get("/{user_id}", response_model=UserResponse, dependencies=[admin_only])
def get_user(user_id: int, db: Session = Depends(get_db)):
    """`{user_id}` in the path becomes the `user_id` argument (like [FromRoute])."""
    return user_service.get_user_by_id(db, user_id)


@router.patch("/{user_id}", response_model=UserResponse, dependencies=[admin_only])
def admin_update_user(user_id: int, data: UserAdminUpdate, db: Session = Depends(get_db)):
    """Change a user's role or activate/deactivate them."""
    return user_service.admin_update_user(db, user_id, data)
