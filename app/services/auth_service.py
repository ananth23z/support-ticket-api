"""
app/services/auth_service.py
============================
WHAT:  Login logic: check email + password, then issue a JWT.
WHY:   Kept separate from user_service because "authentication" is its own concern.

LOGIN FLOW:
    1. find user by email
    2. verify password against the stored Argon2 hash
    3. make sure the account is active
    4. create a signed JWT containing the user's id and role
"""

from sqlalchemy.orm import Session

from app.core.exceptions import UnauthorizedError
from app.core.security import create_access_token, verify_password
from app.services.user_service import get_user_by_email


def login(db: Session, email: str, password: str) -> str:
    user = get_user_by_email(db, email)

    # SECURITY TIP: use the SAME error message whether the email is unknown or the
    # password is wrong. Otherwise an attacker can discover which emails are registered.
    if user is None or not verify_password(password, user.hashed_password):
        raise UnauthorizedError("Incorrect email or password")

    if not user.is_active:
        raise UnauthorizedError("This account has been deactivated")

    return create_access_token(user_id=user.id, role=user.role.value)
