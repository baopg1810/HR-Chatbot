from pathlib import Path

import pytest

from src.models.schemas import DocumentCreate
from src.services.documents import create_document, reset_document_store
from src.services.demo_users import DEMO_USERS
from src.services import llm
from src.services.llm import build_cited_answer
from src.services.retrieval import search_policy_chunks


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


def test_google_api_keys_are_rotated(monkeypatch):
    class Settings:
        google_api_keys = "key-a, key-b; key-c"
        google_api_key = "key-a"

    monkeypatch.setattr(llm, "get_settings", lambda: Settings())
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
