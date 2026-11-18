"""
tests/conftest.py
=================
WHAT:  Shared test setup ("fixtures") that pytest loads automatically.
WHY:   Tests must NOT touch the real tickets.db. We give every test a brand-new,
       empty, IN-MEMORY SQLite database and swap it into the app using
       FastAPI's `dependency_overrides`. This is the payoff of dependency injection:
       we replace get_db without changing a single line of application code.

ASP.NET ANALOGY:
    Like using `WebApplicationFactory<Program>` and replacing the DbContext
    registration with an in-memory database in ConfigureTestServices.

WHAT IS A FIXTURE?
    A function marked @pytest.fixture. A test that has a parameter with the same
    name receives the fixture's value automatically, e.g.
        def test_something(client, admin_token): ...
    (pytest's own little dependency injection!)
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.main import app
from app.models import Role
from app.services.user_service import create_user


@pytest.fixture()
def db_session():
    """A fresh in-memory database for EACH test (tests never affect each other)."""
    # "sqlite://" (no file name) = in-memory database.
    # StaticPool = reuse one connection, otherwise each connection would get its OWN empty DB.
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(db_session):
    """An HTTP client that talks to our app, using the test database."""

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    # We don't use `with TestClient(app)` so the startup lifespan (which would
    # create the REAL tickets.db) does not run during tests.
    yield TestClient(app)
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Helper fixtures: ready-made users + their tokens
# ---------------------------------------------------------------------------
def _login(client: TestClient, email: str, password: str) -> dict:
    """Log in and return the Authorization header dict to pass to requests."""
    response = client.post("/auth/login", data={"username": email, "password": password})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture()
def admin_headers(client, db_session):
    create_user(db_session, "admin@test.com", "Admin", "Admin@123", Role.ADMIN)
    return _login(client, "admin@test.com", "Admin@123")


@pytest.fixture()
def agent(db_session):
    return create_user(db_session, "agent@test.com", "Agent Smith", "Agent@123", Role.AGENT)


@pytest.fixture()
def agent_headers(client, agent):
    return _login(client, "agent@test.com", "Agent@123")


@pytest.fixture()
def customer_headers(client, db_session):
    create_user(db_session, "cust@test.com", "Customer One", "Cust@1234", Role.CUSTOMER)
    return _login(client, "cust@test.com", "Cust@1234")


@pytest.fixture()
def other_customer_headers(client, db_session):
    create_user(db_session, "cust2@test.com", "Customer Two", "Cust@1234", Role.CUSTOMER)
    return _login(client, "cust2@test.com", "Cust@1234")
