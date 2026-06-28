import pytest
from datetime import datetime, timezone

from app.models.schemas import Citation
from app.services.feedback import reset_feedback_store
from app.services import trending
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
    assert len(data["created_candidates"]) == 1
    candidate = data["created_candidates"][0]
    assert candidate["title"] == "Nghỉ phép"
    assert candidate["source_query_count"] == 5
    assert "Toi hoi ve nghi phep" in candidate["summary"]
    assert "chunk-" not in candidate["summary"].lower()
    assert "nhân viên" in candidate["summary"].lower() or "nghỉ phép" in candidate["summary"].lower()

    pins_before_approval = await client.get("/api/v1/trending/pins", headers={"Authorization": f"Bearer {employee_token}"})
    assert pins_before_approval.status_code == 200
    assert pins_before_approval.json()["pins"] == []

    approve_response = await client.post(
        f"/api/v1/admin/trending/candidates/{candidate['id']}/pin",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert approve_response.status_code == 200
    assert approve_response.json()["title"] == "Nghỉ phép"
    assert "chunk-" not in approve_response.json()["summary"].lower()


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
    assert data["created_candidates"] == []
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
    assert read_response.json()["pins"] == []

    run_response = await client.post(
        "/api/v1/admin/trending/run",
        headers={"Authorization": f"Bearer {employee_token}"},
        json={"window_minutes": 60, "threshold": 5},
    )
    assert run_response.status_code == 403

    candidates_response = await client.get(
        "/api/v1/admin/trending/candidates",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert candidates_response.status_code == 200
    assert len(candidates_response.json()["candidates"]) == 1


def test_training_development_query_gets_readable_topic_title(monkeypatch):
    prompts: list[str] = []

    def fake_generate(prompt: str) -> str:
        prompts.append(prompt)
        return (
            '{"title":"Đào tạo và phát triển",'
            '"summary":"Nhân viên chính thức được đào tạo và phát triển theo kế hoạch nhân sự của công ty."}'
        )

    monkeypatch.setattr(trending, "generate_text", fake_generate)
    query = "Nhân viên chính thức được đào tạo và phát triển như thế nào?"
    items = [
        trending.QueryLog(
            message_id=f"msg-{index}",
            user_id="user-1",
            query=query,
            topic_key=trending.topic_key(query),
            answer="Nhân viên chính thức được tham gia đào tạo theo kế hoạch phát triển.",
            citations=[
                Citation(
                    document_id="doc-1",
                    document_title="Sổ tay nhân viên",
                    section="chunk-1",
                    excerpt="Nhân viên chính thức được đào tạo và phát triển theo kế hoạch hằng năm.",
                    page=None,
                    score=0.9,
                )
            ],
            created_at=datetime.now(timezone.utc),
        )
        for index in range(2)
    ]

    draft = trending._build_trend_draft_content(
        topic_key=trending.topic_key(query),
        items=items,
        citations=items[0].citations,
    )

    assert prompts
    assert trending.topic_key(query) == "dao-tao-phat-trien"
    assert draft.title == "Đào tạo và phát triển"
    assert draft.title != "Ao Chinh Nao"
