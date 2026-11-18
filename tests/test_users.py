"""
tests/test_users.py
===================
Profile endpoints and admin-only user management (role-based access control).
"""


def test_get_my_profile(client, customer_headers):
    response = client.get("/users/me", headers=customer_headers)
    assert response.status_code == 200
    assert response.json()["email"] == "cust@test.com"


def test_update_my_profile(client, customer_headers):
    response = client.put("/users/me", json={"full_name": "Renamed"}, headers=customer_headers)
    assert response.status_code == 200
    assert response.json()["full_name"] == "Renamed"


def test_admin_can_create_agent(client, admin_headers):
    response = client.post(
        "/users",
        json={"email": "ag@test.com", "full_name": "New Agent", "password": "Agent@123", "role": "agent"},
        headers=admin_headers,
    )
    assert response.status_code == 201
    assert response.json()["role"] == "agent"


def test_customer_cannot_list_users(client, customer_headers):
    response = client.get("/users", headers=customer_headers)
    assert response.status_code == 403  # logged in, but not allowed


def test_admin_can_list_and_filter_users(client, admin_headers, agent):
    response = client.get("/users?role=agent", headers=admin_headers)
    assert response.status_code == 200
    assert [u["email"] for u in response.json()] == ["agent@test.com"]


def test_deactivated_user_cannot_log_in(client, admin_headers, agent):
    client.patch(f"/users/{agent.id}", json={"is_active": False}, headers=admin_headers)
    response = client.post("/auth/login", data={"username": "agent@test.com", "password": "Agent@123"})
    assert response.status_code == 401
