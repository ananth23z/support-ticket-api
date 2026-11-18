"""
app/core/config.py
==================
WHAT:  One central place for all application settings (secrets, DB URL, token lifetime...).
WHY:   Hard-coding values all over the code makes them hard to change. Keeping them
       in one file means you change a setting once and the whole app picks it up.

ASP.NET ANALOGY:
    This is the Python version of `appsettings.json` + `IConfiguration` / `IOptions<T>`.
    Values are read from ENVIRONMENT VARIABLES first, and fall back to safe defaults
    for local development. In production you would set e.g. SECRET_KEY as an env var.

WHO USES IT:
    - core/database.py  -> DATABASE_URL
    - core/security.py  -> SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES
    - main.py           -> APP_NAME, default admin credentials
"""

import os


class Settings:
    """
    A plain Python class holding settings as class attributes.

    `os.getenv("NAME", "default")` reads an environment variable called NAME.
    If it is not set, the default value is used instead.
    """

    # ---- General ---------------------------------------------------------
    APP_NAME: str = os.getenv("APP_NAME", "Support Ticket Management API")
    APP_VERSION: str = "1.0.0"

    # ---- Database --------------------------------------------------------
    # SQLite stores the whole database in ONE file (tickets.db) in the project folder.
    # To move to PostgreSQL later you would only change this string, e.g.
    # "postgresql://user:password@localhost:5432/tickets"
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./tickets.db")

    # ---- Security / JWT --------------------------------------------------
    # SECRET_KEY is used to SIGN tokens. Anyone who knows it can forge tokens,
    # so in real life it must be long, random and kept secret (never commit it!).
    # Generate one with:  python -c "import secrets; print(secrets.token_hex(32))"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "change-me-in-production-please-use-a-long-random-string")
    ALGORITHM: str = "HS256"  # HMAC + SHA-256: the most common JWT signing algorithm
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

    # ---- First admin user ------------------------------------------------
    # Public registration only creates CUSTOMERS (we never let strangers make
    # themselves admin). So we create ONE admin automatically on startup.
    # Log in with these, then use the admin endpoints to create agents.
    DEFAULT_ADMIN_EMAIL: str = os.getenv("DEFAULT_ADMIN_EMAIL", "admin@example.com")
    DEFAULT_ADMIN_PASSWORD: str = os.getenv("DEFAULT_ADMIN_PASSWORD", "Admin@123")


# A single shared instance. Other files do:  from app.core.config import settings
# (Like registering IOptions<Settings> as a singleton in ASP.NET.)
settings = Settings()
