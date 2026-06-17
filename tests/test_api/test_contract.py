import re
from pathlib import Path

import pytest

from src.services.documents import reset_document_store
from src.services.feedback import reset_feedback_store
from src.services.tickets import reset_ticket_store
from src.services.trending import reset_trending_store


CONTRACT_PATH = Path("flow/05-contract.md")


@pytest.fixture(autouse=True)
def clean_contract_state():
    reset_document_store()
    reset_ticket_store()
    reset_trending_store()
    reset_feedback_store()
    yield
    reset_feedback_store()
    reset_trending_store()
    reset_ticket_store()
    reset_document_store()


async def _token(client, email: str, password: str) -> str:
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return response.json()["access_token"]


def _contract_endpoints() -> list[tuple[str, str, str]]:
    rows = []
    pattern = re.compile(r"^\|\s*(GET|POST|PATCH)\s*\|\s*`([^`]+)`\s*\|\s*(public|token|admin)\s*\|")
    for line in CONTRACT_PATH.read_text(encoding="utf-8").splitlines():
        match = pattern.match(line)
        if match:
            method, path, auth = match.groups()
            rows.append((method.lower(), path, auth))
    return rows


@pytest.mark.asyncio
async def test_contract_endpoints_exist_in_openapi(client):
    response = await client.get("/openapi.json")
    assert response.status_code == 200
    paths = response.json()["paths"]

    missing = []
    for method, path, _auth in _contract_endpoints():
        if path not in paths or method not in paths[path]:
            missing.append(f"{method.upper()} {path}")

    assert not missing, f"Missing contract endpoints from OpenAPI: {missing}"


@pytest.mark.asyncio
async def test_contract_response_components_have_required_shape(client):
    response = await client.get("/openapi.json")
    assert response.status_code == 200
    schemas = response.json()["components"]["schemas"]

    expected_properties = {
        "ChatResponse": {
            "message_id",
            "session_id",
            "answer",
            "citations",
            "actions",
            "escalated_ticket_id",
            "refusal_reason",
        },
        "Ticket": {
            "id",
            "requester_id",
            "status",
            "priority",
            "reason",
            "summary",
            "assignee_id",
            "created_at",
            "updated_at",
        },
        "TrendPin": {
            "id",
            "title",
            "summary",
            "source_query_count",
            "citations",
            "created_at",
            "expires_at",
        },
        "PersonalHrMetrics": {
            "employee_id",
            "leave_days_remaining",
            "insurance_status",
            "reward_review_status",
            "as_of_date",
        },
    }

    for schema_name, properties in expected_properties.items():
        assert schema_name in schemas
        assert properties <= set(schemas[schema_name]["properties"])


@pytest.mark.asyncio
async def test_contract_auth_behavior_for_public_token_and_admin_endpoints(client):
    employee_token = await _token(client, "employee@example.com", "employee123")
    employee_headers = {"Authorization": f"Bearer {employee_token}"}

    public_health = await client.get("/health")
    public_login = await client.post(
        "/api/v1/auth/login",
        json={"email": "employee@example.com", "password": "employee123"},
    )
    assert public_health.status_code == 200
    assert public_login.status_code == 200

    token_checks = [
        ("get", "/api/v1/me", None),
        ("post", "/api/v1/chat", {"message": "Hello", "session_id": None}),
        ("get", "/api/v1/me/hr-metrics", None),
        (
            "post",
            "/api/v1/escalations",
            {"session_id": None, "message": "Need help", "reason": "user_requested", "priority": "normal"},
        ),
        ("get", "/api/v1/trending/pins", None),
        ("post", "/api/v1/feedback", {"message_id": "msg-missing", "rating": "up"}),
    ]
    for method, path, body in token_checks:
        response = await getattr(client, method)(path, json=body) if body is not None else await getattr(client, method)(path)
        assert response.status_code == 401, f"{method.upper()} {path} should require token"

    admin_checks = [
        ("post", "/api/v1/documents", {"title": "Doc", "content": "Content"}),
        ("get", "/api/v1/documents", None),
        ("get", "/api/v1/admin/tickets", None),
        ("patch", "/api/v1/admin/tickets/ticket-missing", {"status": "in_progress"}),
        ("post", "/api/v1/admin/trending/run", {"window_minutes": 60, "threshold": 5}),
    ]
    for method, path, body in admin_checks:
        response = (
            await getattr(client, method)(path, headers=employee_headers, json=body)
            if body is not None
            else await getattr(client, method)(path, headers=employee_headers)
        )
        assert response.status_code == 403, f"{method.upper()} {path} should require admin role"


@pytest.mark.asyncio
async def test_contract_happy_path_response_shapes(client):
    employee_token = await _token(client, "employee@example.com", "employee123")
    admin_token = await _token(client, "admin@example.com", "admin123")
    employee_headers = {"Authorization": f"Bearer {employee_token}"}
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    chat = await client.post(
        "/api/v1/chat",
        headers=employee_headers,
        json={"message": "Toi can hoi ve chinh sach nghi phep.", "session_id": None},
    )
    assert chat.status_code == 200
    chat_data = chat.json()
    assert {
        "message_id",
        "session_id",
        "answer",
        "citations",
        "actions",
        "escalated_ticket_id",
        "refusal_reason",
    } <= set(chat_data)

    metrics = await client.get("/api/v1/me/hr-metrics", headers=employee_headers)
    assert metrics.status_code == 200
    assert {
        "employee_id",
        "leave_days_remaining",
        "insurance_status",
        "reward_review_status",
        "as_of_date",
    } <= set(metrics.json())

    ticket = await client.post(
        "/api/v1/escalations",
        headers=employee_headers,
        json={"session_id": None, "message": "Need HR", "reason": "user_requested", "priority": "normal"},
    )
    assert ticket.status_code == 200
    ticket_data = ticket.json()
    assert {
        "id",
        "requester_id",
        "status",
        "priority",
        "reason",
        "summary",
        "assignee_id",
        "created_at",
        "updated_at",
    } <= set(ticket_data)

    updated = await client.patch(
        f"/api/v1/admin/tickets/{ticket_data['id']}",
        headers=admin_headers,
        json={"status": "in_progress", "assignee_id": "hr-001"},
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "in_progress"

    for index in range(5):
        await client.post(
            "/api/v1/chat",
            headers=employee_headers,
            json={"message": f"Toi hoi ve nghi phep lan {index}", "session_id": None},
        )
    trend = await client.post(
        "/api/v1/admin/trending/run",
        headers=admin_headers,
        json={"window_minutes": 60, "threshold": 5},
    )
    assert trend.status_code == 200
    pin = trend.json()["created_pins"][0]
    assert {"id", "title", "summary", "source_query_count", "citations", "created_at", "expires_at"} <= set(pin)

    feedback = await client.post(
        "/api/v1/feedback",
        headers=employee_headers,
        json={"message_id": chat_data["message_id"], "rating": "up", "comment": "OK"},
    )
    assert feedback.status_code == 200
    assert feedback.json() == {"ok": True}
