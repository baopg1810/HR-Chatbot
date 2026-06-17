import pytest

from src.services.documents import reset_document_store


@pytest.fixture(autouse=True)
def clean_document_store():
    reset_document_store()
    yield
    reset_document_store()


async def _employee_token(client) -> str:
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "employee@example.com", "password": "employee123"},
    )
    return response.json()["access_token"]


@pytest.mark.asyncio
async def test_chat_requires_token_for_valid_message(client):
    response = await client.post("/api/v1/chat", json={"message": "Hello", "session_id": None})

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_chat_returns_contract_shape(client):
    token = await _employee_token(client)

    response = await client.post(
        "/api/v1/chat",
        json={"message": "Toi can hoi ve chinh sach nghi phep.", "session_id": None},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["message_id"].startswith("msg-")
    assert data["session_id"].startswith("session-")
    assert data["answer"]
    assert data["citations"] == []
    assert data["actions"][0]["type"] == "none"
    assert data["escalated_ticket_id"] is None
    assert data["refusal_reason"] is None


@pytest.mark.asyncio
async def test_chat_reuses_session_id(client):
    token = await _employee_token(client)

    response = await client.post(
        "/api/v1/chat",
        json={"message": "Hello", "session_id": "session-demo"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["session_id"] == "session-demo"


@pytest.mark.asyncio
async def test_chat_stream_returns_sse_events(client):
    token = await _employee_token(client)

    response = await client.post(
        "/api/v1/chat/stream",
        json={"message": "Hello", "session_id": None},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    body = response.text
    assert "event: start" in body
    assert "event: token" in body
    assert "event: done" in body
    assert '"message_id"' in body
    assert '"session_id"' in body
