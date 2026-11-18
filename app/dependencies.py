"""
app/dependencies.py
===================
WHAT:  Reusable "dependencies" that endpoints ask for:
         - get_db              -> a database session         (re-exported from core/database.py)
         - get_current_user    -> the logged-in User, read from the JWT
         - require_roles(...)  -> "only these roles may call this endpoint"
WHY:   Without this, EVERY endpoint would repeat: read the header, decode the token,
       load the user, check the role... Dependencies let us write that ONCE.

HOW FASTAPI DEPENDENCY INJECTION WORKS (the most important FastAPI idea!):
    def my_endpoint(user: User = Depends(get_current_user)):
        ...
    Before calling `my_endpoint`, FastAPI sees `Depends(get_current_user)`, calls
    `get_current_user` (which itself depends on the token and the DB session, so
    FastAPI resolves those first), and passes the result in as `user`.
    Dependencies can depend on other dependencies -> a "dependency tree".

ASP.NET ANALOGY:
    - Depends(get_db)               ~ constructor injection of a scoped DbContext
    - Depends(get_current_user)     ~ [Authorize] + reading HttpContext.User
    - Depends(require_roles(ADMIN)) ~ [Authorize(Roles = "Admin")]
"""

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.security import decode_access_token
from app.models import Role, User

# OAuth2PasswordBearer does two things:
#   1. At runtime: reads the header "Authorization: Bearer <token>" and gives us <token>.
#      If the header is missing it returns 401 automatically.
#   2. In Swagger: adds the green "Authorize" button that logs in via `tokenUrl`.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),  # step 1: get the raw token string
    db: Session = Depends(get_db),        # step 2: get a DB session
) -> User:
    """Turn a token into a User object, or raise 401."""
    payload = decode_access_token(token)
    if payload is None:
        raise UnauthorizedError("Invalid or expired token")

    user_id = payload.get("sub")
    if user_id is None:
        raise UnauthorizedError("Invalid token payload")

    # db.get(Model, primary_key) is the fastest way to load one row by id
    # (like DbContext.Find(id) in EF).
    user = db.get(User, int(user_id))
    if user is None or not user.is_active:
        raise UnauthorizedError("User not found or inactive")

    return user


def require_roles(*allowed_roles: Role):
    """
    A *dependency factory*: a function that BUILDS and returns a dependency.

    Usage in a router:
        @router.get("/users", dependencies=[Depends(require_roles(Role.ADMIN))])
    or, when you also need the user object:
        def endpoint(user: User = Depends(require_roles(Role.ADMIN, Role.AGENT))):

    `*allowed_roles` means "accept any number of roles as arguments".
    """

    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        # Note: this inner function itself depends on get_current_user,
        # so authentication (401) always happens BEFORE authorization (403).
        if current_user.role not in allowed_roles:
            allowed = ", ".join(r.value for r in allowed_roles)
            raise ForbiddenError(f"This action requires one of these roles: {allowed}")
        return current_user

    return role_checker


__all__ = ["get_db", "get_current_user", "require_roles", "oauth2_scheme"]
