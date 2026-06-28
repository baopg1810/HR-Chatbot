import pytest
import pytest_asyncio


@pytest_asyncio.fixture(autouse=True)
async def clean_ticket_store():
    from app.database.session import get_db_context
    from app.models.ticket import Ticket as DBTicket
    from sqlalchemy import delete
    async with get_db_context() as db:
        await db.execute(delete(DBTicket))
        await db.commit()
    yield
    async with get_db_context() as db:
        await db.execute(delete(DBTicket))
        await db.commit()


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
    assert data["id"].startswith("TCK-")
    assert data["requester_id"] == "emp-001"
    assert data["status"] == "open"
    assert data["reason"] == "Toi can HR xem ho tru truong hop nay."


@pytest.mark.asyncio
async def test_chat_requires_confirmation_for_explicit_ticket_request(client):
    token = await _token(client, "employee@example.com", "employee123")

    response = await client.post(
        "/api/v1/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "message": "Tao ticket giup toi ve viec hop dong thu viec chua duoc phan hoi",
            "session_id": "session-chat-ticket",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["actions"][0]["type"] == "escalation_confirmation_required"
    assert data["actions"][0]["data"]["reason"] == "user_requested"
    assert data["escalated_ticket_id"] is None


@pytest.mark.asyncio
async def test_chat_requires_confirmation_from_detail_after_ticket_prompt(client):
    token = await _token(client, "employee@example.com", "employee123")
    session_id = "session-chat-ticket-followup"

    first_response = await client.post(
        "/api/v1/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={"message": "giup toi tao ticket di", "session_id": session_id},
    )
    assert first_response.status_code == 200
    first_data = first_response.json()
    assert first_data["actions"][0]["type"] == "none"
    assert "nội dung cần HR hỗ trợ" in first_data["answer"]

    second_response = await client.post(
        "/api/v1/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={"message": "toi muon nghi viec han", "session_id": session_id},
    )
    assert second_response.status_code == 200
    second_data = second_response.json()
    assert second_data["actions"][0]["type"] == "escalation_confirmation_required"
    assert second_data["actions"][0]["data"]["message"] == "toi muon nghi viec han"
    assert second_data["escalated_ticket_id"] is None


@pytest.mark.asyncio
async def test_employee_can_list_only_own_tickets(client):
    employee_token = await _token(client, "employee@example.com", "employee123")
    admin_token = await _token(client, "admin@example.com", "admin123")

    own_ticket = await client.post(
        "/api/v1/escalations",
        headers={"Authorization": f"Bearer {employee_token}"},
        json={
            "session_id": None,
            "message": "Ticket cua nhan vien.",
            "reason": "user_requested",
            "priority": "normal",
        },
    )
    await client.post(
        "/api/v1/escalations",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "session_id": None,
            "message": "Ticket cua admin.",
            "reason": "user_requested",
            "priority": "normal",
        },
    )

    response = await client.get("/api/v1/tickets", headers={"Authorization": f"Bearer {employee_token}"})

    assert response.status_code == 200
    data = response.json()
    assert [ticket["id"] for ticket in data["tickets"]] == [own_ticket.json()["id"]]
    assert data["tickets"][0]["reason"] == "Ticket cua nhan vien."


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
async def test_hr_admin_can_reject_ticket(client):
    employee_token = await _token(client, "employee@example.com", "employee123")
    admin_token = await _token(client, "admin@example.com", "admin123")
    create_response = await client.post(
        "/api/v1/escalations",
        headers={"Authorization": f"Bearer {employee_token}"},
        json={
            "session_id": None,
            "message": "Yeu cau khong thuoc pham vi xu ly.",
            "reason": "user_requested",
            "priority": "normal",
        },
    )
    ticket_id = create_response.json()["id"]

    patch_response = await client.patch(
        f"/api/v1/admin/tickets/{ticket_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"status": "rejected", "assignee_id": "hr-001", "internal_note": "Tu choi xu ly"},
    )

    assert patch_response.status_code == 200
    data = patch_response.json()
    assert data["status"] == "rejected"
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
    assert "/api/v1/tickets" in paths
    assert "/api/v1/admin/tickets" in paths
    assert "/api/v1/admin/tickets/{ticket_id}" in paths
