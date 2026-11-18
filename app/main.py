"""
app/main.py
===========
WHAT:  The ENTRY POINT. Creates the FastAPI app and wires every piece together.
WHY:   Something has to connect config, database, middleware, error handlers and
       routers. That "composition root" lives here.

ASP.NET ANALOGY:
    This file is `Program.cs`:
        var builder = WebApplication.CreateBuilder();   -> app = FastAPI(...)
        app.UseMiddleware<RequestLogging>();            -> app.add_middleware(...)
        app.UseExceptionHandler(...)                    -> register_exception_handlers(app)
        app.MapControllers();                           -> app.include_router(...)
        db.Database.EnsureCreated();                    -> Base.metadata.create_all(...)

RUN IT:
    uvicorn app.main:app --reload
      - `app.main` = the file app/main.py ;  `:app` = the variable named `app` below
      - --reload   = restart automatically when you save a file (development only)
    Then open http://127.0.0.1:8000/docs  for Swagger UI.

THE FULL REQUEST FLOW (keep this picture in mind):
    Client
      -> Uvicorn (web server)
      -> RequestLoggingMiddleware            (middleware/)
      -> Router endpoint matched by URL      (routers/)
           -> Pydantic validates the body     (schemas/)   -> 422 if invalid
           -> Depends(): get_db, get_current_user, require_roles  (dependencies.py)
      -> Service applies business rules      (services/)   -> raises AppException if not allowed
      -> SQLAlchemy reads/writes the DB      (models/ + core/database.py)
      <- Response serialized via response_model (schemas/)
      <- Exception handlers format errors    (core/exceptions.py)
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.config import settings
from app.core.database import Base, SessionLocal, engine
from app.core.exceptions import register_exception_handlers
from app.core.logging_config import setup_logging
from app.middleware.logging_middleware import RequestLoggingMiddleware
from app.routers import auth, tickets, users
from app.services.user_service import ensure_default_admin

# Importing app.models registers User and Ticket on Base.metadata (see models/__init__.py)
from app import models  # noqa: F401

setup_logging()


# ---------------------------------------------------------------------------
# LIFESPAN: code that runs once at STARTUP (before `yield`) and SHUTDOWN (after).
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1) Create tables if they don't exist yet. (Fine for learning/SQLite.
    #    Real projects use a migration tool like Alembic ~ EF Core Migrations.)
    Base.metadata.create_all(bind=engine)

    # 2) Make sure there is at least one admin to log in with.
    db = SessionLocal()
    try:
        ensure_default_admin(db, settings.DEFAULT_ADMIN_EMAIL, settings.DEFAULT_ADMIN_PASSWORD)
    finally:
        db.close()

    yield  # <-- the application runs and serves requests here

    # (shutdown code would go here, e.g. closing connections)


# ---------------------------------------------------------------------------
# CREATE THE APP
# ---------------------------------------------------------------------------
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "A simple Support Ticket Management API.\n\n"
        "**Quick start:** click **Authorize**, log in with "
        f"`{settings.DEFAULT_ADMIN_EMAIL}` / `{settings.DEFAULT_ADMIN_PASSWORD}` "
        "(email goes in the *username* box)."
    ),
    lifespan=lifespan,
)

# Middleware (runs around every request)
app.add_middleware(RequestLoggingMiddleware)

# Centralized error handling
register_exception_handlers(app)

# Routers (each one adds a group of endpoints)
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(tickets.router)


@app.get("/", tags=["Health"])
def health_check():
    """A tiny endpoint to check the server is alive (useful for monitoring)."""
    return {"status": "ok", "app": settings.APP_NAME, "docs": "/docs"}
