from pathlib import Path

import pytest

from app.models.schemas import DocumentCreate
from app.services.documents import create_document, reset_document_store
from app.services.demo_users import DEMO_USERS
from app.services import llm
from app.services.llm import build_cited_answer
from app.services.retrieval import search_policy_chunks


@pytest.fixture(autouse=True)
def clean_document_store():
    reset_document_store()
    yield
    reset_document_store()


def test_retrieval_returns_citation_for_relevant_policy():
    content = Path("tests/fixtures/hr_policy_leave.txt").read_text(encoding="utf-8")
    create_document(
        DocumentCreate(
            title="Chinh sach nghi phep",
            content=content,
            visibility_roles=["employee", "hr_admin"],
            department_ids=[],
        )
    )

    citations = search_policy_chunks("Nhan vien co bao nhieu ngay nghi phep nam?", DEMO_USERS["employee@example.com"])

    assert citations
    assert citations[0].document_title == "Chinh sach nghi phep"
    assert "12 ngay nghi phep" in citations[0].excerpt


def test_build_cited_answer_uses_primary_citation():
    content = Path("tests/fixtures/hr_policy_leave.txt").read_text(encoding="utf-8")
    create_document(
        DocumentCreate(
            title="Chinh sach nghi phep",
            content=content,
            visibility_roles=["employee", "hr_admin"],
            department_ids=[],
        )
    )
    citations = search_policy_chunks("nghi phep nam", DEMO_USERS["employee@example.com"])

    answer = build_cited_answer("nghi phep nam", citations)

    assert "Chinh sach nghi phep" in answer
    assert "12 ngay nghi phep" in answer


def test_build_cited_answer_extracts_best_supported_sentence():
    citation = llm.Citation(
        document_id="doc-1",
        document_title="Chinh sach nghi phep",
        section="1.1 - Nghi phep nam",
        excerpt=(
            "Quy dinh nay ap dung cho toan cong ty. "
            "Nhan vien chinh thuc co 12 ngay nghi phep nam moi nam. "
            "Nhan vien can bao truoc cho quan ly truc tiep."
        ),
        score=0.9,
    )

    answer = build_cited_answer("Nhan vien co bao nhieu ngay nghi phep nam?", [citation])

    assert "Chinh sach nghi phep" in answer
    assert "12 ngay nghi phep nam" in answer
    assert "bao truoc cho quan ly" not in answer


def test_build_cited_answer_prefers_gemini_generation(monkeypatch):
    citation = llm.Citation(
        document_id="doc-1",
        document_title="Chính sách nghỉ phép",
        section="1.1",
        excerpt="Nhân viên có 12 ngày nghỉ phép năm.",
        score=0.9,
    )
    monkeypatch.setattr(llm, "_generate_with_gemini", lambda prompt: "Câu trả lời từ Gemini")

    answer = build_cited_answer("Tôi có bao nhiêu ngày phép?", [citation])

    assert answer == "Câu trả lời từ Gemini"


def test_build_cited_answer_hides_internal_chunk_reference(monkeypatch):
    citation = llm.Citation(
        document_id="doc-1",
        document_title="So tay nhan vien",
        section="chunk-26",
        excerpt="Nhan vien can bao truoc 3 ngay lam viec khi nghi phep.",
        score=0.9,
    )
    captured_prompts = []

    def fake_generate(prompt):
        captured_prompts.append(prompt)
        return "Theo So tay nhan vien - chunk-26, can bao truoc 3 ngay."

    monkeypatch.setattr(llm, "_generate_text_with_ttft", fake_generate)

    answer = build_cited_answer("Can bao truoc bao lau?", [citation])

    assert "chunk-26" not in captured_prompts[0]
    assert "chunk-26" not in answer
    assert "So tay nhan vien" in answer


def test_build_conversation_context_summarizes_older_turns():
    history = [
        ("user", "Q1"),
        ("assistant", "A1"),
        ("user", "Q2"),
        ("assistant", "A2"),
        ("user", "Q3"),
        ("assistant", "A3"),
        ("user", "Q4"),
        ("assistant", "A4"),
    ]

    context = llm.build_conversation_context(history)

    assert "Tóm tắt các trao đổi cũ hơn" in context
    assert "Người dùng hỏi: Q1" in context
    assert "[1] Người dùng: Q2" in context
    assert "[2] Người dùng: Q3" in context
    assert "[3] Người dùng: Q4" in context
    assert "[1] Người dùng: Q1" not in context


def test_general_prompt_includes_conversation_context(monkeypatch):
    captured_prompts = []
    monkeypatch.setattr(llm, "_generate_with_gemini", lambda prompt: captured_prompts.append(prompt) or "ok")

    answer = llm.build_general_answer("Câu hiện tại", "Nguyễn Văn A", conversation_context="Ngữ cảnh cũ")

    assert answer == "ok"
    assert "LỊCH SỬ HỘI THOẠI:\nNgữ cảnh cũ" in captured_prompts[0]
    assert "Câu hỏi: Câu hiện tại" in captured_prompts[0]


def test_stream_cited_answer_prefers_gemini_tokens(monkeypatch):
    citation = llm.Citation(
        document_id="doc-1",
        document_title="Chinh sach nghi phep",
        section="1.1",
        excerpt="Nhan vien co 12 ngay nghi phep nam.",
        score=0.9,
    )
    monkeypatch.setattr(llm, "_stream_with_gemini", lambda prompt: iter(["Theo ", "nguon."]))

    tokens = list(llm.stream_cited_answer("nghi phep nam", [citation]))

    assert tokens == ["Theo ", "nguon."]


def test_stream_with_gemini_records_time_to_first_token(monkeypatch):
    class Settings:
        app_env = "development"
        llm_temperature = 0.2
        model_name = "gemini-test"

    class FakeGeneration:
        def __init__(self):
            self.updates = []

        def update(self, **kwargs):
            self.updates.append(kwargs)

    class FakeLangfuse:
        def __init__(self, generation):
            self.generation = generation

        def start_as_current_observation(self, **kwargs):
            return self

        def __enter__(self):
            return self.generation

        def __exit__(self, exc_type, exc, traceback):
            return False

    class FakeResult:
        def __init__(self, text):
            self.text = text

    class FakeModels:
        def generate_content_stream(self, **kwargs):
            return [FakeResult("Theo "), FakeResult("nguon.")]

    class FakeGeminiClient:
        models = FakeModels()

    generation = FakeGeneration()
    monkeypatch.setattr(llm, "get_settings", lambda: Settings())
    monkeypatch.setattr(llm, "get_client", lambda: FakeLangfuse(generation))
    monkeypatch.setattr(llm, "_ordered_google_api_keys", lambda: ["key-a"])
    monkeypatch.setattr(llm, "_running_under_pytest", lambda: False)
    monkeypatch.setattr(llm, "_gemini_client", lambda api_key: FakeGeminiClient())

    tokens = list(llm._stream_with_gemini("prompt"))

    ttft_updates = [update for update in generation.updates if "completion_start_time" in update]
    assert tokens == ["Theo ", "nguon."]
    assert len(ttft_updates) == 1
    assert ttft_updates[0]["completion_start_time"].tzinfo is not None
    assert ttft_updates[0]["metadata"]["time_to_first_token_ms"] >= 0


def test_google_api_keys_are_rotated(monkeypatch):
    class Settings:
        google_api_keys = "key-a, key-b; key-c"
        google_api_key = "key-a"

    monkeypatch.setattr(llm, "get_settings", lambda: Settings())
    monkeypatch.setattr(llm, "_numbered_google_api_keys", lambda: [])
    monkeypatch.setattr(llm, "_NEXT_KEY_INDEX", 0)

    assert llm._ordered_google_api_keys() == ["key-a", "key-b", "key-c"]
    assert llm._ordered_google_api_keys() == ["key-b", "key-c", "key-a"]
    assert llm._ordered_google_api_keys() == ["key-c", "key-a", "key-b"]


@pytest.mark.asyncio
async def test_chat_returns_citation_for_covered_policy_question(client):
    admin_login = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "admin123"},
    )
    admin_token = admin_login.json()["access_token"]
    content = Path("tests/fixtures/hr_policy_leave.txt").read_text(encoding="utf-8")

    upload = await client.post(
        "/api/v1/documents",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "title": "Chinh sach nghi phep",
            "content": content,
            "visibility_roles": ["employee", "hr_admin"],
            "department_ids": [],
        },
    )
    assert upload.status_code == 200

    employee_login = await client.post(
        "/api/v1/auth/login",
        json={"email": "employee@example.com", "password": "employee123"},
    )
    employee_token = employee_login.json()["access_token"]
    response = await client.post(
        "/api/v1/chat",
        headers={"Authorization": f"Bearer {employee_token}"},
        json={"message": "Nhan vien co bao nhieu ngay nghi phep nam?", "session_id": None},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["citations"]
    assert data["citations"][0]["document_title"] == "Chinh sach nghi phep"
    assert data["citations"][0]["section"] or data["citations"][0]["page"] is not None
    assert data["citations"][0]["excerpt"]
