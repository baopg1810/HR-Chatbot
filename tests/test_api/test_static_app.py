import pytest

from app.services.documents import reset_document_store
from app.services.feedback import reset_feedback_store
from app.services.tickets import reset_ticket_store
from app.services.trending import reset_trending_store


@pytest.fixture(autouse=True)
def clean_static_app_state():
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


@pytest.mark.asyncio
async def test_static_frontend_is_served(client):
    app_response = await client.get("/app")
    static_response = await client.get("/static/hr-helpdesk.html")

    assert app_response.status_code == 200
    assert static_response.status_code == 200
    html = app_response.text
    assert '<div id="root"></div>' in html
    assert "/app/assets/" in html
    asset_path = html.split('src="', maxsplit=1)[1].split('"', maxsplit=1)[0]
    asset_response = await client.get(asset_path)
    assert asset_response.status_code == 200
    bundle = asset_response.text
    assert "/api/v1" in bundle
    assert "/auth/login" in bundle
    assert "/chat/stream" in bundle
    assert "/documents/upload" in bundle
    assert "/admin/tickets" in bundle
    assert "/admin/trending/run" in bundle
    assert "/api/v1/chat/stream" in static_response.text
    assert "<pre" not in html.lower()


@pytest.mark.asyncio
async def test_employee_frontend_flow_policy_metrics_and_feedback(client):
    employee_token = await _token(client, "employee@example.com", "employee123")
    admin_token = await _token(client, "admin@example.com", "admin123")
    employee_headers = {"Authorization": f"Bearer {employee_token}"}
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    upload = await client.post(
        "/api/v1/documents",
        headers=admin_headers,
        json={
            "title": "Chinh sach nghi phep",
            "content": "Nhan vien chinh thuc co 12 ngay nghi phep nam moi nam.",
            "visibility_roles": ["employee", "hr_admin"],
            "department_ids": [],
        },
    )
    assert upload.status_code == 200

    policy = await client.post(
        "/api/v1/chat",
        headers=employee_headers,
        json={"message": "Toi can hoi ve chinh sach nghi phep.", "session_id": None},
    )
    assert policy.status_code == 200
    policy_data = policy.json()
    assert policy_data["citations"]

    metrics = await client.post(
        "/api/v1/chat",
        headers=employee_headers,
        json={"message": "Toi con bao nhieu ngay phep?", "session_id": None},
    )
    assert metrics.status_code == 200
    assert metrics.json()["actions"][0]["type"] == "hr_metric_lookup"

    feedback = await client.post(
        "/api/v1/feedback",
        headers=employee_headers,
        json={"message_id": policy_data["message_id"], "rating": "up", "comment": "Huu ich"},
    )
    assert feedback.status_code == 200
    assert feedback.json() == {"ok": True}


@pytest.mark.asyncio
async def test_admin_frontend_flow_tickets_trending_and_documents(client):
    employee_token = await _token(client, "employee@example.com", "employee123")
    admin_token = await _token(client, "admin@example.com", "admin123")
    employee_headers = {"Authorization": f"Bearer {employee_token}"}
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    upload = await client.post(
        "/api/v1/documents",
        headers=admin_headers,
        json={
            "title": "Chinh sach nghi phep",
            "content": "Nhan vien chinh thuc co 12 ngay nghi phep nam moi nam.",
            "visibility_roles": ["employee", "hr_admin"],
            "department_ids": [],
        },
    )
    assert upload.status_code == 200

    documents = await client.get("/api/v1/documents", headers=admin_headers)
    assert documents.status_code == 200
    assert documents.json()["documents"][0]["title"] == "Chinh sach nghi phep"

    escalation = await client.post(
        "/api/v1/escalations",
        headers=employee_headers,
        json={
            "message": "Can HR xu ly thu cong truong hop nay.",
            "reason": "user_requested",
            "priority": "normal",
            "session_id": None,
        },
    )
    assert escalation.status_code == 200
    ticket_id = escalation.json()["id"]
    assert ticket_id

    tickets = await client.get("/api/v1/admin/tickets", headers=admin_headers)
    assert tickets.status_code == 200
    assert tickets.json()["tickets"][0]["id"] == ticket_id

    updated = await client.patch(
        f"/api/v1/admin/tickets/{ticket_id}",
        headers=admin_headers,
        json={"status": "in_progress", "assignee_id": "hr-001"},
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "in_progress"

    for index in range(5):
        response = await client.post(
            "/api/v1/chat",
            headers=employee_headers,
            json={"message": f"Toi hoi ve nghi phep lan {index}", "session_id": None},
        )
        assert response.status_code == 200

    trend = await client.post(
        "/api/v1/admin/trending/run",
        headers=admin_headers,
        json={"window_minutes": 60, "threshold": 5},
    )
    assert trend.status_code == 200
    candidate = trend.json()["created_candidates"][0]
    assert candidate["title"] == "Nghỉ phép"

    approved = await client.post(
        f"/api/v1/admin/trending/candidates/{candidate['id']}/pin",
        headers=admin_headers,
    )
    assert approved.status_code == 200

    pins = await client.get("/api/v1/trending/pins", headers=employee_headers)
    assert pins.status_code == 200
    assert len(pins.json()["pins"]) == 1
