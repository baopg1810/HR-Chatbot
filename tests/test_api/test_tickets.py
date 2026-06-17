import pytest

from src.services.tickets import reset_ticket_store


@pytest.fixture(autouse=True)
def clean_ticket_store():
    reset_ticket_store()
    yield
    reset_ticket_store()


async def _token(client, email: str, password: str) -> str:
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.mark.asyncio
async def test_employee_can_create_escalation_ticket(client):
    token = await _token(client, "employee@example.com", "employee123")

    response = await client.post(
        "/api/v1/escalations",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "session_id": "session-demo",
            "message": "Toi can HR xem ho tru truong hop nay.",
            "reason": "user_requested",
            "priority": "normal",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"].startswith("ticket-")
    assert data["requester_id"] == "emp-001"
    assert data["status"] == "open"


@pytest.mark.asyncio
async def test_hr_admin_can_list_and_patch_tickets(client):
    employee_token = await _token(client, "employee@example.com", "employee123")
    admin_token = await _token(client, "admin@example.com", "admin123")
    create_response = await client.post(
        "/api/v1/escalations",
        headers={"Authorization": f"Bearer {employee_token}"},
        json={
            "session_id": None,
            "message": "Can HR xu ly thu cong.",
            "reason": "user_requested",
            "priority": "high",
        },
    )
    ticket_id = create_response.json()["id"]

    list_response = await client.get("/api/v1/admin/tickets", headers={"Authorization": f"Bearer {admin_token}"})
    assert list_response.status_code == 200
    assert list_response.json()["tickets"][0]["id"] == ticket_id

    patch_response = await client.patch(
        f"/api/v1/admin/tickets/{ticket_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"status": "in_progress", "assignee_id": "hr-001", "internal_note": "Dang xu ly"},
    )
    assert patch_response.status_code == 200
    data = patch_response.json()
    assert data["status"] == "in_progress"
    assert data["assignee_id"] == "hr-001"


@pytest.mark.asyncio
async def test_employee_cannot_list_admin_tickets(client):
    token = await _token(client, "employee@example.com", "employee123")

    response = await client.get("/api/v1/admin/tickets", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_ticket_and_metrics_endpoints_appear_in_openapi(client):
    response = await client.get("/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/api/v1/me/hr-metrics" in paths
    assert "/api/v1/escalations" in paths
    assert "/api/v1/admin/tickets" in paths
    assert "/api/v1/admin/tickets/{ticket_id}" in paths
