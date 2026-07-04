import pytest
import pytest_asyncio


@pytest_asyncio.fixture(autouse=True)
async def clean_ticket_store():
    from app.database.session import get_db_context
    from app.models.chat_session_state import ChatSessionState
    from app.models.ticket import Ticket as DBTicket
    from app.services.documents import reset_document_store
    from sqlalchemy import delete
    reset_document_store()
    async with get_db_context() as db:
        await db.execute(delete(ChatSessionState))
        await db.execute(delete(DBTicket))
        await db.commit()
    yield
    reset_document_store()
    async with get_db_context() as db:
        await db.execute(delete(ChatSessionState))
        await db.execute(delete(DBTicket))
        await db.commit()


async def _token(client, email: str, password: str) -> str:
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.mark.asyncio
async def test_employee_can_create_escalation_ticket(client):
    token = await _token(client, "employee@example.com", "employee123")

    response = await client.post(
        "/api/v1/escalations",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "session_id": "session-demo",
            "message": "Toi can HR xem ho tru truong hop nay.",
            "reason": "user_requested",
            "priority": "normal",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"].startswith("TCK-")
    assert data["requester_id"] == "emp-001"
    assert data["status"] == "open"
    assert data["reason"] == "Toi can HR xem ho tru truong hop nay."


@pytest.mark.asyncio
async def test_chat_requires_confirmation_for_explicit_ticket_request(client):
    token = await _token(client, "employee@example.com", "employee123")

    response = await client.post(
        "/api/v1/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "message": "Tao ticket giup toi ve viec hop dong thu viec chua duoc phan hoi",
            "session_id": "session-chat-ticket",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["actions"][0]["type"] == "ticket_draft_confirmation"
    assert data["actions"][0]["data"]["reason"] == "user_requested"
    assert data["actions"][0]["data"]["title"] == "Hỗ trợ xử lý hợp đồng"
    assert data["actions"][0]["data"]["category"] == "documents"
    assert data["escalated_ticket_id"] is None


@pytest.mark.asyncio
async def test_chat_requires_confirmation_from_detail_after_ticket_prompt(client):
    token = await _token(client, "employee@example.com", "employee123")
    session_id = "session-chat-ticket-followup"

    first_response = await client.post(
        "/api/v1/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={"message": "giup toi tao ticket di", "session_id": session_id},
    )
    assert first_response.status_code == 200
    first_data = first_response.json()
    assert first_data["actions"][0]["type"] == "none"
    assert "mô tả chi tiết vấn đề" in first_data["answer"]

    second_response = await client.post(
        "/api/v1/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={"message": "toi muon nghi viec han", "session_id": session_id},
    )
    assert second_response.status_code == 200
    second_data = second_response.json()
    assert second_data["actions"][0]["type"] == "ticket_draft_confirmation"
    assert second_data["actions"][0]["data"]["title"] == "Hỗ trợ thủ tục nghỉ việc"
    assert second_data["actions"][0]["data"]["category"] == "documents"
    assert second_data["actions"][0]["data"]["description"] == "toi muon nghi viec han"
    assert second_data["escalated_ticket_id"] is None


@pytest.mark.asyncio
async def test_new_ticket_intent_creates_session_state(client):
    from app.database.session import get_db_context
    from app.services.chat_session_state import get_chat_session_state

    token = await _token(client, "employee@example.com", "employee123")
    session_id = "session-chat-state-create"

    response = await client.post(
        "/api/v1/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={"message": "tôi muốn tạo ticket", "session_id": session_id},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["actions"][0]["type"] == "none"
    async with get_db_context() as db:
        state = await get_chat_session_state(db, session_id)
    assert state.active_flow == "ticket_draft"
    assert state.pending_ticket_draft is not None
    assert state.pending_ticket_draft.session_id == session_id


@pytest.mark.asyncio
async def test_payroll_delay_followup_uses_session_state_and_completes_draft(client):
    token = await _token(client, "employee@example.com", "employee123")
    session_id = "session-chat-state-payroll"

    first_response = await client.post(
        "/api/v1/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={"message": "tôi muốn tạo ticket", "session_id": session_id},
    )
    assert first_response.status_code == 200

    second_response = await client.post(
        "/api/v1/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={"message": "tôi bị chậm lương tháng 6", "session_id": session_id},
    )

    assert second_response.status_code == 200
    data = second_response.json()
    assert data["refusal_reason"] is None
    assert data["actions"][0]["type"] == "ticket_draft_confirmation"
    assert data["actions"][0]["data"]["title"] == "Chậm lương tháng 6"
    assert data["actions"][0]["data"]["category"] == "other"
    assert "chậm lương tháng 6" in data["actions"][0]["data"]["description"].lower()
    assert data["actions"][0]["data"]["priority"] == "high"


@pytest.mark.asyncio
async def test_short_ticket_followup_uses_session_state_without_out_of_scope_fallback(client):
    token = await _token(client, "employee@example.com", "employee123")
    session_id = "session-chat-state-short-followup"

    first_response = await client.post(
        "/api/v1/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={"message": "tôi muốn tạo ticket", "session_id": session_id},
    )
    assert first_response.status_code == 200

    second_response = await client.post(
        "/api/v1/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={"message": "thiết bị", "session_id": session_id},
    )

    assert second_response.status_code == 200
    data = second_response.json()
    assert data["actions"][0]["type"] == "none"
    assert "không thể hỗ trợ" not in data["answer"].lower()


@pytest.mark.asyncio
async def test_policy_question_during_ticket_draft_pauses_without_contaminating_ticket_context(client):
    from app.database.session import get_db_context
    from app.models.schemas import DocumentCreate
    from app.services.chat_session_state import get_chat_session_state
    from app.services.documents import create_document

    create_document(
        DocumentCreate(
            title="Chinh sach nghi phep",
            content="Nhan vien chinh thuc co 12 ngay nghi phep nam moi nam.",
            visibility_roles=["employee", "hr_admin"],
            department_ids=[],
        )
    )
    token = await _token(client, "employee@example.com", "employee123")
    session_id = "session-ticket-policy-pause"

    first_response = await client.post(
        "/api/v1/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={"message": "toi muon tao ticket", "session_id": session_id},
    )
    assert first_response.status_code == 200
    async with get_db_context() as db:
        state_before_policy = await get_chat_session_state(db, session_id)
    ticket_context_before = state_before_policy.ticket_context

    policy_response = await client.post(
        "/api/v1/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={"message": "Chinh sach nghi phep nam nhu the nao?", "session_id": session_id},
    )

    assert policy_response.status_code == 200
    policy_data = policy_response.json()
    assert "Ticket đang được tạm giữ" in policy_data["answer"]
    assert policy_data["actions"][0]["type"] in {"none", "escalation_confirmation_required"}
    async with get_db_context() as db:
        state_after_policy = await get_chat_session_state(db, session_id)
    assert state_after_policy.active_flow == "ticket_draft"
    assert state_after_policy.ticket_context == ticket_context_before
    assert "Chinh sach nghi phep" not in state_after_policy.ticket_context

    detail_response = await client.post(
        "/api/v1/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={"message": "toi muon nghi viec han", "session_id": session_id},
    )

    assert detail_response.status_code == 200
    detail_data = detail_response.json()
    assert detail_data["actions"][0]["type"] == "ticket_draft_confirmation"
    assert detail_data["actions"][0]["data"]["description"] == "toi muon nghi viec han"


@pytest.mark.asyncio
async def test_chat_history_restores_pending_ticket_draft_action(client):
    token = await _token(client, "employee@example.com", "employee123")
    session_id = "session-ticket-history-draft"

    response = await client.post(
        "/api/v1/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={"message": "Tao ticket giup toi ve viec hop dong thu viec chua duoc phan hoi", "session_id": session_id},
    )
    assert response.status_code == 200
    assert response.json()["actions"][0]["type"] == "ticket_draft_confirmation"

    history_response = await client.get(
        f"/api/v1/chat/sessions/{session_id}/messages",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert history_response.status_code == 200
    messages = history_response.json()
    ai_messages = [message for message in messages if message["sender"] == "ai"]
    assert ai_messages
    restored_actions = ai_messages[-1]["actions"]
    assert restored_actions[0]["type"] == "ticket_draft_confirmation"
    assert restored_actions[0]["data"]["title"] == "Hỗ trợ xử lý hợp đồng"
    assert restored_actions[0]["data"]["session_id"] == session_id


@pytest.mark.asyncio
async def test_ticket_submit_success_clears_session_state(client):
    from app.database.session import get_db_context
    from app.services.chat_session_state import get_chat_session_state

    token = await _token(client, "employee@example.com", "employee123")
    session_id = "session-chat-state-submit"

    await client.post(
        "/api/v1/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={"message": "tôi muốn tạo ticket", "session_id": session_id},
    )
    ticket_response = await client.post(
        "/api/v1/escalations",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "session_id": session_id,
            "message": "Tiêu đề: Test\nDanh mục: Khác\n\nMô tả:\nTest ticket.",
            "reason": "user_requested",
            "priority": "normal",
        },
    )

    assert ticket_response.status_code == 200
    async with get_db_context() as db:
        state = await get_chat_session_state(db, session_id)
    assert state.active_flow == "none"
    assert state.pending_ticket_draft is None


@pytest.mark.asyncio
async def test_ticket_cancel_clears_session_state(client):
    from app.database.session import get_db_context
    from app.services.chat_session_state import get_chat_session_state

    token = await _token(client, "employee@example.com", "employee123")
    session_id = "session-chat-state-cancel"

    await client.post(
        "/api/v1/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={"message": "tôi muốn tạo ticket", "session_id": session_id},
    )
    clear_response = await client.post(
        f"/api/v1/chat/sessions/{session_id}/state/clear",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert clear_response.status_code == 200
    async with get_db_context() as db:
        state = await get_chat_session_state(db, session_id)
    assert state.active_flow == "none"
    assert state.pending_ticket_draft is None


@pytest.mark.asyncio
async def test_employee_can_list_only_own_tickets(client):
    employee_token = await _token(client, "employee@example.com", "employee123")
    admin_token = await _token(client, "admin@example.com", "admin123")

    own_ticket = await client.post(
        "/api/v1/escalations",
        headers={"Authorization": f"Bearer {employee_token}"},
        json={
            "session_id": None,
            "message": "Ticket cua nhan vien.",
            "reason": "user_requested",
            "priority": "normal",
        },
    )
    await client.post(
        "/api/v1/escalations",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "session_id": None,
            "message": "Ticket cua admin.",
            "reason": "user_requested",
            "priority": "normal",
        },
    )

    response = await client.get("/api/v1/tickets", headers={"Authorization": f"Bearer {employee_token}"})

    assert response.status_code == 200
    data = response.json()
    assert [ticket["id"] for ticket in data["tickets"]] == [own_ticket.json()["id"]]
    assert data["tickets"][0]["reason"] == "Ticket cua nhan vien."


@pytest.mark.asyncio
async def test_hr_admin_can_list_and_patch_tickets(client):
    employee_token = await _token(client, "employee@example.com", "employee123")
    admin_token = await _token(client, "admin@example.com", "admin123")
    create_response = await client.post(
        "/api/v1/escalations",
        headers={"Authorization": f"Bearer {employee_token}"},
        json={
            "session_id": None,
            "message": "Can HR xu ly thu cong.",
            "reason": "user_requested",
            "priority": "high",
        },
    )
    ticket_id = create_response.json()["id"]

    list_response = await client.get("/api/v1/admin/tickets", headers={"Authorization": f"Bearer {admin_token}"})
    assert list_response.status_code == 200
    assert list_response.json()["tickets"][0]["id"] == ticket_id

    patch_response = await client.patch(
        f"/api/v1/admin/tickets/{ticket_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"status": "in_progress", "assignee_id": "hr-001", "internal_note": "Dang xu ly"},
    )
    assert patch_response.status_code == 200
    data = patch_response.json()
    assert data["status"] == "in_progress"
    assert data["assignee_id"] == "hr-001"


@pytest.mark.asyncio
async def test_hr_admin_can_reject_ticket(client):
    employee_token = await _token(client, "employee@example.com", "employee123")
    admin_token = await _token(client, "admin@example.com", "admin123")
    create_response = await client.post(
        "/api/v1/escalations",
        headers={"Authorization": f"Bearer {employee_token}"},
        json={
            "session_id": None,
            "message": "Yeu cau khong thuoc pham vi xu ly.",
            "reason": "user_requested",
            "priority": "normal",
        },
    )
    ticket_id = create_response.json()["id"]

    patch_response = await client.patch(
        f"/api/v1/admin/tickets/{ticket_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"status": "rejected", "assignee_id": "hr-001", "internal_note": "Tu choi xu ly"},
    )

    assert patch_response.status_code == 200
    data = patch_response.json()
    assert data["status"] == "rejected"
    assert data["assignee_id"] == "hr-001"


@pytest.mark.asyncio
async def test_employee_cannot_list_admin_tickets(client):
    token = await _token(client, "employee@example.com", "employee123")

    response = await client.get("/api/v1/admin/tickets", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_ticket_and_metrics_endpoints_appear_in_openapi(client):
    response = await client.get("/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/api/v1/me/hr-metrics" in paths
    assert "/api/v1/escalations" in paths
    assert "/api/v1/tickets" in paths
    assert "/api/v1/admin/tickets" in paths
    assert "/api/v1/admin/tickets/{ticket_id}" in paths
