import pytest

from app.services.feedback import reset_feedback_store
from app.services.trending import reset_trending_store


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


@pytest.mark.asyncio
async def test_feedback_accepts_up_and_down_for_valid_message_id(client):
    token = await _token(client, "employee@example.com", "employee123")
    chat_response = await client.post(
        "/api/v1/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={"message": "Toi can hoi ve chinh sach nghi phep.", "session_id": None},
    )
    message_id = chat_response.json()["message_id"]

    up_response = await client.post(
        "/api/v1/feedback",
        headers={"Authorization": f"Bearer {token}"},
        json={"message_id": message_id, "rating": "up", "comment": "Huu ich"},
    )
    down_response = await client.post(
        "/api/v1/feedback",
        headers={"Authorization": f"Bearer {token}"},
        json={"message_id": message_id, "rating": "down", "comment": "Can ro hon"},
    )

    assert up_response.status_code == 200
    assert up_response.json() == {"ok": True}
    assert down_response.status_code == 200
    assert down_response.json() == {"ok": True}


@pytest.mark.asyncio
async def test_feedback_rejects_unknown_message_id(client):
    token = await _token(client, "employee@example.com", "employee123")

    response = await client.post(
        "/api/v1/feedback",
        headers={"Authorization": f"Bearer {token}"},
        json={"message_id": "msg-missing", "rating": "up"},
    )

    assert response.status_code == 404
