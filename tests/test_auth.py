"""
tests/test_auth.py
==================
API tests for registration, login and token protection.

Every test follows the AAA pattern:
    Arrange - set up data   |   Act - call the API   |   Assert - check the result
Run all tests with:  pytest -v
"""

from app.core.security import hash_password, verify_password


def test_register_creates_customer(client):
    response = client.post(
        "/auth/register",
        json={"email": "new@test.com", "full_name": "New User", "password": "Password1"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "new@test.com"
    assert body["role"] == "customer"          # public sign-up is always a customer
    assert "password" not in body              # secrets are never returned
    assert "hashed_password" not in body


def test_register_duplicate_email_returns_409(client):
    payload = {"email": "dup@test.com", "full_name": "Dup", "password": "Password1"}
    client.post("/auth/register", json=payload)
    response = client.post("/auth/register", json=payload)
    assert response.status_code == 409
    assert response.json()["error"] == "Conflict"


def test_register_invalid_data_returns_422(client):
    response = client.post(
        "/auth/register", json={"email": "not-an-email", "full_name": "X", "password": "123"}
    )
    assert response.status_code == 422
    assert response.json()["error"] == "Validation Error"


def test_login_success_returns_token(client):
    client.post("/auth/register", json={"email": "a@test.com", "full_name": "Al", "password": "Password1"})
    response = client.post("/auth/login", data={"username": "a@test.com", "password": "Password1"})
    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"
    assert len(response.json()["access_token"]) > 20


def test_login_wrong_password_returns_401(client):
    client.post("/auth/register", json={"email": "b@test.com", "full_name": "Bo", "password": "Password1"})
    response = client.post("/auth/login", data={"username": "b@test.com", "password": "WRONG-pass"})
    assert response.status_code == 401


def test_protected_endpoint_requires_token(client):
    assert client.get("/users/me").status_code == 401


def test_invalid_token_is_rejected(client):
    response = client.get("/users/me", headers={"Authorization": "Bearer this.is.fake"})
    assert response.status_code == 401


def test_password_hashing_unit():
    """A pure UNIT test: no HTTP, no database - just the function."""
    hashed = hash_password("MySecret1")
    assert hashed != "MySecret1"
    assert hashed.startswith("$argon2")
    assert verify_password("MySecret1", hashed) is True
    assert verify_password("wrong", hashed) is False
