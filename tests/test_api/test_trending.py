import pytest

from src.services.feedback import reset_feedback_store
from src.services.trending import reset_trending_store


@pytest.fixture(autouse=True)
def clean_stores():
    reset_trending_store()
    reset_feedback_store()
    yield
    reset_feedback_store()
    reset_trending_store()


async def _token(client, email: str, password: str) -> str:
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return response.json()["access_token"]


async def _ask_leave_questions(client, token: str, count: int) -> None:
    for index in range(count):
        response = await client.post(
            "/api/v1/chat",
            headers={"Authorization": f"Bearer {token}"},
            json={"message": f"Toi hoi ve nghi phep lan {index}", "session_id": None},
        )
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_five_similar_queries_create_one_trend_pin(client):
    employee_token = await _token(client, "employee@example.com", "employee123")
    admin_token = await _token(client, "admin@example.com", "admin123")
    await _ask_leave_questions(client, employee_token, 5)

    response = await client.post(
        "/api/v1/admin/trending/run",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"window_minutes": 60, "threshold": 5},
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data["created_pins"]) == 1
    assert data["created_pins"][0]["title"] == "Nghỉ phép"
    assert data["created_pins"][0]["source_query_count"] == 5


@pytest.mark.asyncio
async def test_four_similar_queries_do_not_create_trend_pin_at_threshold_five(client):
    employee_token = await _token(client, "employee@example.com", "employee123")
    admin_token = await _token(client, "admin@example.com", "admin123")
    await _ask_leave_questions(client, employee_token, 4)

    response = await client.post(
        "/api/v1/admin/trending/run",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"window_minutes": 60, "threshold": 5},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["created_pins"] == []
    assert "nghi-phep" in data["skipped_topics"]


@pytest.mark.asyncio
async def test_employee_can_read_pins_but_cannot_run_trending(client):
    employee_token = await _token(client, "employee@example.com", "employee123")
    admin_token = await _token(client, "admin@example.com", "admin123")
    await _ask_leave_questions(client, employee_token, 5)
    await client.post(
        "/api/v1/admin/trending/run",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"window_minutes": 60, "threshold": 5},
    )

    read_response = await client.get("/api/v1/trending/pins", headers={"Authorization": f"Bearer {employee_token}"})
    assert read_response.status_code == 200
    assert len(read_response.json()["pins"]) == 1

    run_response = await client.post(
        "/api/v1/admin/trending/run",
        headers={"Authorization": f"Bearer {employee_token}"},
        json={"window_minutes": 60, "threshold": 5},
    )
    assert run_response.status_code == 403
