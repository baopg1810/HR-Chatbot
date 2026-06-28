from uuid import uuid4

import pytest

from app.services import llm
from app.services.documents import reset_document_store


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
async def test_chat_rate_limit_allows_10_questions_per_minute(client):
    from app.services.rate_limit import chat_rate_limiter
    original_limit = chat_rate_limiter.limit
    chat_rate_limiter.limit = 10
    try:
        token = await _employee_token(client)

        for index in range(10):
            response = await client.post(
                "/api/v1/chat",
                json={"message": f"Hello {index}", "session_id": "session-rate-limit"},
                headers={"Authorization": f"Bearer {token}"},
            )
            assert response.status_code == 200

        response = await client.post(
            "/api/v1/chat",
            json={"message": "Hello limit", "session_id": "session-rate-limit"},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 429
        assert response.headers["retry-after"]
        assert "10 câu trong 1 phút" in response.json()["detail"]
    finally:
        chat_rate_limiter.limit = original_limit


@pytest.mark.asyncio
async def test_chat_session_history_records_user_and_assistant_messages(client):
    token = await _employee_token(client)
    session_id = "session-history-test"
    message = "History check message"

    response = await client.post(
        "/api/v1/chat",
        json={"message": message, "session_id": session_id},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200

    sessions_response = await client.get(
        "/api/v1/chat/sessions",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert sessions_response.status_code == 200
    assert any(session["title"] == message for session in sessions_response.json())

    messages_response = await client.get(
        f"/api/v1/chat/sessions/{session_id}/messages",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert messages_response.status_code == 200
    messages = messages_response.json()
    assert any(item["sender"] == "user" and item["text"] == message for item in messages)
    assert any(item["sender"] == "ai" and item["text"] for item in messages)


@pytest.mark.asyncio
async def test_chat_prompt_includes_saved_history_for_same_session(client, monkeypatch):
    captured_prompts = []
    monkeypatch.setattr(llm, "_generate_with_gemini", lambda prompt: captured_prompts.append(prompt) or f"answer {len(captured_prompts)}")
    token = await _employee_token(client)
    session_id = f"session-{uuid4()}"

    first_response = await client.post(
        "/api/v1/chat",
        json={"message": "History prompt question one", "session_id": session_id},
        headers={"Authorization": f"Bearer {token}"},
    )
    second_response = await client.post(
        "/api/v1/chat",
        json={"message": "History prompt question two", "session_id": session_id},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert "LỊCH SỬ HỘI THOẠI" in captured_prompts[-1]
    assert "History prompt question one" in captured_prompts[-1]
    assert "answer 1" in captured_prompts[-1]
    assert "Câu hỏi: History prompt question two" in captured_prompts[-1]


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


@pytest.mark.asyncio
async def test_chat_stream_sends_live_llm_tokens_before_done(client, monkeypatch):
    from app.api.v1.endpoints import chat as chat_endpoint

    monkeypatch.setattr(chat_endpoint, "stream_general_answer", lambda *args, **kwargs: iter(["A", "B"]))
    token = await _employee_token(client)

    response = await client.post(
        "/api/v1/chat/stream",
        json={"message": "Hello", "session_id": None},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    body = response.text
    first_token_index = body.index('event: token\ndata: {"text": "A"}')
    second_token_index = body.index('event: token\ndata: {"text": "B"}')
    done_index = body.index("event: done")
    assert first_token_index < second_token_index < done_index
    assert '"answer": "AB"' in body
