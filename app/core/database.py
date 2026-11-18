"""
app/core/database.py
====================
WHAT:  Sets up the connection to the database using SQLAlchemy.
WHY:   Every part of the app that reads/writes data needs a database "session".
       This file creates the engine (the connection pool) and a factory for sessions.

ASP.NET ANALOGY:
    - `engine`         ~ the connection string + provider configured in Program.cs
    - `SessionLocal()` ~ creating a new `DbContext` instance
    - `Base`           ~ the base class all entity classes are registered with
    - `get_db()`       ~ `services.AddDbContext<AppDbContext>()` with a SCOPED lifetime:
                         one session per HTTP request, disposed at the end.

FLOW:
    request arrives -> FastAPI calls get_db() -> a new Session is opened
    -> the router/service uses it -> request ends -> session is closed.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings

# ---------------------------------------------------------------------------
# 1) ENGINE: knows HOW to talk to the database.
# ---------------------------------------------------------------------------
# `check_same_thread=False` is needed ONLY for SQLite: by default SQLite refuses
# to be used from a different thread than the one that opened it, but FastAPI
# may handle a request on a different thread. Other databases don't need this.
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {},
)

# ---------------------------------------------------------------------------
# 2) SESSION FACTORY: calling SessionLocal() gives you a fresh Session.
# ---------------------------------------------------------------------------
# A Session is your "unit of work": you add/modify objects, then commit().
# autoflush=False -> SQLAlchemy won't silently send SQL before we ask it to.
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


# ---------------------------------------------------------------------------
# 3) BASE CLASS for models: every table class inherits from this.
# ---------------------------------------------------------------------------
# SQLAlchemy collects all subclasses in Base.metadata, which is how
# `Base.metadata.create_all(engine)` (in main.py) knows which tables to create.
class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# 4) DEPENDENCY: gives each request its own session and always closes it.
# ---------------------------------------------------------------------------
def get_db():
    """
    This is a *generator* function (it uses `yield` instead of `return`).

    FastAPI treats it specially:
      - code BEFORE `yield` runs before your endpoint (open the session)
      - the yielded value is injected into your endpoint
      - code AFTER `yield` (the `finally`) runs after the response is sent

    So the session is ALWAYS closed, even if the endpoint raises an error.
    It's the same idea as a C# `using (var db = new AppDbContext()) { ... }`.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
