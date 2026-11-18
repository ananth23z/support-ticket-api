"""
app/routers/auth.py
===================
WHAT:  Public endpoints: register and login.
WHY:   These are the only endpoints you can call WITHOUT a token.

ROUTER = a group of related endpoints (like an ASP.NET Controller).
    router = APIRouter(prefix="/auth", tags=["Authentication"])
      - prefix -> every route here starts with /auth   (like [Route("auth")])
      - tags   -> groups them under one heading in Swagger UI

ENDPOINT ANATOMY (read this once, it applies to every router file):
    @router.post("/register", response_model=UserResponse, status_code=201)
    def register(data: UserRegister, db: Session = Depends(get_db)):
        |            |                    |
        |            |                    +-- injected dependency (DB session)
        |            +-- request BODY, validated by Pydantic automatically
        +-- HTTP method + path  (like [HttpPost("register")])
    response_model -> FastAPI filters/serializes the return value through this schema
    status_code    -> HTTP code on success (201 Created for new resources)
"""

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.models import Role
from app.schemas.auth import TokenResponse
from app.schemas.user import UserRegister, UserResponse
from app.services import auth_service, user_service

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(data: UserRegister, db: Session = Depends(get_db)):
    """Create a new **customer** account. (Agents/admins are created by an admin.)"""
    # Note how thin this is: the router just passes data to the service.
    # Role is FORCED to CUSTOMER here, so nobody can register as admin.
    return user_service.create_user(
        db, email=data.email, full_name=data.full_name, password=data.password, role=Role.CUSTOMER
    )


@router.post("/login", response_model=TokenResponse)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """
    Log in and receive a JWT access token.

    This endpoint reads FORM data (not JSON) with fields `username` and `password`,
    because that is what the OAuth2 standard - and Swagger's **Authorize** button - sends.
    Put your **email** in the `username` field.
    """
    token = auth_service.login(db, email=form.username, password=form.password)
    return TokenResponse(access_token=token)
