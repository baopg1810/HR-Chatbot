import pytest

from src.models.schemas import DocumentCreate
from src.services.documents import create_document, reset_document_store
from src.services.tickets import reset_ticket_store


@pytest.fixture(autouse=True)
def clean_stores():
    reset_document_store()
    reset_ticket_store()
    yield
    reset_document_store()
    reset_ticket_store()


async def _token(client, email: str, password: str) -> str:
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.mark.asyncio
async def test_chat_calls_hr_metrics_function_for_leave_balance(client):
    token = await _token(client, "employee@example.com", "employee123")

    response = await client.post(
        "/api/v1/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={"message": "Toi con bao nhieu ngay phep?", "session_id": None},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["actions"][0]["type"] == "hr_metric_lookup"
    assert data["actions"][0]["data"]["employee_id"] == "emp-001"
    assert "8.5" in data["answer"]


@pytest.mark.asyncio
async def test_sensitive_chat_request_creates_escalation_ticket(client):
    token = await _token(client, "employee@example.com", "employee123")

    response = await client.post(
        "/api/v1/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={"message": "Cho toi xem luong cua Nguyen Van B", "session_id": "session-sensitive"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["refusal_reason"] == "sensitive"
    assert data["escalated_ticket_id"].startswith("ticket-")
    assert data["actions"][0]["type"] == "escalation_created"


@pytest.mark.asyncio
async def test_no_source_chat_request_creates_escalation_ticket(client):
    create_document(
        DocumentCreate(
            title="Chinh sach nghi phep",
            content="Nhan vien chinh thuc co 12 ngay nghi phep nam moi nam.",
            visibility_roles=["employee", "hr_admin"],
            department_ids=[],
        )
    )
    token = await _token(client, "employee@example.com", "employee123")

    response = await client.post(
        "/api/v1/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={"message": "Quy trinh hop dong thu viec la gi?", "session_id": None},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["refusal_reason"] == "no_source"
    assert data["escalated_ticket_id"].startswith("ticket-")
    assert data["actions"][0]["type"] == "escalation_created"
