"""
tests/test_tickets.py
=====================
The full ticket life-cycle plus permissions, search, filter, sort and pagination.
"""


def create_ticket(client, headers, title="Login problem", priority="medium"):
    """Small helper so each test doesn't repeat the same POST."""
    response = client.post(
        "/tickets",
        json={"title": title, "description": "Detailed description of the issue", "priority": priority},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


# ---- Create & view --------------------------------------------------------
def test_customer_creates_ticket(client, customer_headers):
    ticket = create_ticket(client, customer_headers)
    assert ticket["status"] == "open"              # default status
    assert ticket["assigned_agent"] is None        # not assigned yet
    assert ticket["created_by"]["email"] == "cust@test.com"


def test_agent_cannot_create_ticket(client, agent_headers):
    response = client.post(
        "/tickets", json={"title": "x" * 5, "description": "y" * 20}, headers=agent_headers
    )
    assert response.status_code == 403


def test_customer_sees_only_own_tickets(client, customer_headers, other_customer_headers):
    create_ticket(client, customer_headers, title="Mine")
    create_ticket(client, other_customer_headers, title="Not mine")

    body = client.get("/tickets", headers=customer_headers).json()
    assert body["total"] == 1
    assert body["items"][0]["title"] == "Mine"


def test_customer_cannot_view_other_customers_ticket(client, customer_headers, other_customer_headers):
    ticket = create_ticket(client, other_customer_headers)
    response = client.get(f"/tickets/{ticket['id']}", headers=customer_headers)
    assert response.status_code == 403


def test_get_missing_ticket_returns_404(client, admin_headers):
    response = client.get("/tickets/9999", headers=admin_headers)
    assert response.status_code == 404
    assert response.json()["error"] == "Not Found"


# ---- Assign & status workflow --------------------------------------------
def test_full_workflow_assign_and_resolve(client, customer_headers, admin_headers, agent, agent_headers):
    ticket = create_ticket(client, customer_headers)

    # Agent sees nothing until the ticket is assigned
    assert client.get("/tickets", headers=agent_headers).json()["total"] == 0

    # Admin assigns it
    response = client.patch(f"/tickets/{ticket['id']}/assign", json={"agent_id": agent.id}, headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["assigned_agent"]["id"] == agent.id

    # Agent now sees it and moves it through the statuses
    assert client.get("/tickets", headers=agent_headers).json()["total"] == 1
    for new_status in ["in_progress", "resolved", "closed"]:
        response = client.patch(f"/tickets/{ticket['id']}/status", json={"status": new_status}, headers=agent_headers)
        assert response.status_code == 200
        assert response.json()["status"] == new_status

    # Business rule: an agent can't change a CLOSED ticket
    response = client.patch(f"/tickets/{ticket['id']}/status", json={"status": "open"}, headers=agent_headers)
    assert response.status_code == 400


def test_cannot_assign_to_non_agent(client, customer_headers, admin_headers):
    ticket = create_ticket(client, customer_headers)
    me = client.get("/users/me", headers=customer_headers).json()
    response = client.patch(f"/tickets/{ticket['id']}/assign", json={"agent_id": me["id"]}, headers=admin_headers)
    assert response.status_code == 400


def test_agent_cannot_update_unassigned_ticket(client, customer_headers, agent_headers):
    ticket = create_ticket(client, customer_headers)
    response = client.patch(f"/tickets/{ticket['id']}/status", json={"status": "resolved"}, headers=agent_headers)
    assert response.status_code == 403


def test_customer_cannot_change_status(client, customer_headers):
    ticket = create_ticket(client, customer_headers)
    response = client.patch(f"/tickets/{ticket['id']}/status", json={"status": "closed"}, headers=customer_headers)
    assert response.status_code == 403


def test_invalid_status_value_returns_422(client, admin_headers, customer_headers):
    ticket = create_ticket(client, customer_headers)
    response = client.patch(f"/tickets/{ticket['id']}/status", json={"status": "banana"}, headers=admin_headers)
    assert response.status_code == 422


# ---- Edit & delete --------------------------------------------------------
def test_customer_edits_own_open_ticket(client, customer_headers):
    ticket = create_ticket(client, customer_headers)
    response = client.put(f"/tickets/{ticket['id']}", json={"priority": "high"}, headers=customer_headers)
    assert response.status_code == 200
    assert response.json()["priority"] == "high"
    assert response.json()["title"] == ticket["title"]  # untouched fields stay the same


def test_admin_deletes_ticket(client, customer_headers, admin_headers):
    ticket = create_ticket(client, customer_headers)
    assert client.delete(f"/tickets/{ticket['id']}", headers=admin_headers).status_code == 204
    assert client.get(f"/tickets/{ticket['id']}", headers=admin_headers).status_code == 404


# ---- Search / filter / sort / pagination ---------------------------------
def test_search_filter_sort_and_paginate(client, customer_headers, admin_headers):
    create_ticket(client, customer_headers, title="Printer jammed", priority="low")
    create_ticket(client, customer_headers, title="Server down", priority="critical")
    create_ticket(client, customer_headers, title="Password reset", priority="high")

    # search (case-insensitive, title or description)
    body = client.get("/tickets?search=PRINTER", headers=admin_headers).json()
    assert [t["title"] for t in body["items"]] == ["Printer jammed"]

    # filter by priority
    body = client.get("/tickets?priority=critical", headers=admin_headers).json()
    assert body["total"] == 1 and body["items"][0]["title"] == "Server down"

    # sort by priority, highest first
    body = client.get("/tickets?sort_by=priority&order=desc", headers=admin_headers).json()
    assert [t["priority"] for t in body["items"]] == ["critical", "high", "low"]

    # pagination: 2 per page -> page 2 has the last one
    body = client.get("/tickets?size=2&page=2", headers=admin_headers).json()
    assert body["total"] == 3 and body["pages"] == 2 and len(body["items"]) == 1


def test_stats_admin_only(client, customer_headers, admin_headers):
    create_ticket(client, customer_headers, priority="high")
    assert client.get("/tickets/stats", headers=customer_headers).status_code == 403

    stats = client.get("/tickets/stats", headers=admin_headers).json()
    assert stats["total"] == 1
    assert stats["by_status"]["open"] == 1
    assert stats["by_priority"]["high"] == 1
    assert stats["unassigned"] == 1
