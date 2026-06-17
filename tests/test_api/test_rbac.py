import time

import pytest

from src.models.schemas import DocumentCreate, User
from src.services.auth import create_access_token
from src.services.documents import create_document, reset_document_store


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


def _token_for(user: User) -> str:
    return create_access_token(user)


@pytest.mark.asyncio
async def test_employee_cannot_retrieve_hr_admin_only_citations(client):
    create_document(
        DocumentCreate(
            title="HR Admin Salary Policy",
            content="Chinh sach luong noi bo danh rieng cho HR admin.",
            visibility_roles=["hr_admin"],
            department_ids=[],
        )
    )
    token = await _employee_token(client)

    response = await client.post(
        "/api/v1/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={"message": "chinh sach luong noi bo HR admin", "session_id": None},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["citations"] == []


@pytest.mark.asyncio
async def test_department_admin_only_gets_matching_department_citation(client):
    create_document(
        DocumentCreate(
            title="Quy trinh phong dao tao",
            content="Phong dao tao nop bang cham cong vao thu sau hang tuan.",
            visibility_roles=["department_admin"],
            department_ids=["dept-training"],
        )
    )
    create_document(
        DocumentCreate(
            title="Quy trinh phong tai chinh",
            content="Phong tai chinh doi soat phu cap vao ngay 25 hang thang.",
            visibility_roles=["department_admin"],
            department_ids=["dept-finance"],
        )
    )
    user = User(
        id="dept-admin-001",
        email="training-admin@example.com",
        full_name="Training Admin",
        role="department_admin",
        department_id="dept-training",
    )

    response = await client.post(
        "/api/v1/chat",
        headers={"Authorization": f"Bearer {_token_for(user)}"},
        json={"message": "phong dao tao nop bang cham cong khi nao?", "session_id": None},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["citations"]
    assert data["citations"][0]["document_title"] == "Quy trinh phong dao tao"
    assert all(citation["document_title"] != "Quy trinh phong tai chinh" for citation in data["citations"])


@pytest.mark.asyncio
async def test_covered_policy_prompt_still_returns_quick_cited_answer(client):
    create_document(
        DocumentCreate(
            title="Chinh sach nghi phep",
            content="Nhan vien chinh thuc co 12 ngay nghi phep nam moi nam.",
            visibility_roles=["employee", "hr_admin"],
            department_ids=[],
        )
    )
    token = await _employee_token(client)

    started = time.perf_counter()
    response = await client.post(
        "/api/v1/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={"message": "nhan vien co bao nhieu ngay nghi phep nam?", "session_id": None},
    )
    elapsed = time.perf_counter() - started

    assert response.status_code == 200
    assert elapsed < 10
    data = response.json()
    assert data["citations"]
    assert data["refusal_reason"] is None
