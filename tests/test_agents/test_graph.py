import pytest
import pytest_asyncio
from sqlalchemy import delete

from app.agents.graph import agent
from app.database.session import get_db_context
from app.models.schemas import ChatResponse, DocumentCreate
from app.models.ticket import Ticket as DBTicket
from app.services.demo_users import DEMO_USERS
from app.services.documents import create_document, reset_document_store


@pytest_asyncio.fixture(autouse=True)
async def clean_graph_stores():
    reset_document_store()
    async with get_db_context() as db:
        await db.execute(delete(DBTicket))
        await db.commit()
    yield
    reset_document_store()
    async with get_db_context() as db:
        await db.execute(delete(DBTicket))
        await db.commit()


@pytest.mark.asyncio
async def test_agent_basic_flow():
    result = await agent.ainvoke({"query": "Hello"})
    assert "response" in result
    assert isinstance(result["response"], ChatResponse)


@pytest.mark.asyncio
async def test_agent_capability_question_uses_static_helpdesk_answer():
    result = await agent.ainvoke(
        {
            "query": "Bạn có thể hỗ trợ gì về HR?",
            "current_user": DEMO_USERS["employee@example.com"],
            "session_id": "session-capability",
            "message_id": "msg-capability",
        }
    )

    response = result["response"]
    assert response.refusal_reason is None
    assert "Mình có thể hỗ trợ" in response.answer
    assert "nội dung không được phép hiển thị" not in response.answer


@pytest.mark.asyncio
async def test_bare_numeric_reply_without_pending_choice_asks_for_clarification():
    result = await agent.ainvoke(
        {
            "query": "3",
            "current_user": DEMO_USERS["employee@example.com"],
            "session_id": "session-bare-number",
            "message_id": "msg-bare-number",
            "conversation_context": (
                "3 lượt hỏi đáp gần nhất:\n"
                "[1] Người dùng: Bạn có thể hỗ trợ gì về HR?\n"
                "[1] AI: Mình có thể hỗ trợ các câu hỏi liên quan đến nhân sự."
            ),
        }
    )

    response = result["response"]
    assert response.refusal_reason is None
    assert response.answer != "3"
    assert "nhập rõ câu hỏi HR" in response.answer


@pytest.mark.asyncio
async def test_agent_state_structure():
    result = await agent.ainvoke({"query": "Test query"})
    assert isinstance(result, dict)
    assert "query" in result


@pytest.mark.asyncio
async def test_ticket_intent_without_description_asks_for_details():
    result = await agent.ainvoke(
        {
            "query": "Tôi muốn tạo ticket",
            "current_user": DEMO_USERS["employee@example.com"],
            "session_id": "session-ticket-missing",
            "message_id": "msg-ticket-missing",
        }
    )

    response = result["response"]
    assert "mô tả chi tiết vấn đề" in response.answer
    assert response.actions[0].type == "none"
    assert response.escalated_ticket_id is None


@pytest.mark.asyncio
async def test_ticket_intent_with_description_requires_confirmation():
    result = await agent.ainvoke(
        {
            "query": "Tạo ticket giúp tôi về việc hợp đồng thử việc chưa được phản hồi",
            "current_user": DEMO_USERS["employee@example.com"],
            "session_id": "session-ticket-create",
            "message_id": "msg-ticket-create",
        }
    )

    response = result["response"]
    assert response.actions[0].type == "ticket_draft_confirmation"
    assert response.actions[0].data["reason"] == "user_requested"
    assert response.actions[0].data["title"] == "Hỗ trợ xử lý hợp đồng"
    assert response.actions[0].data["category"] == "documents"
    assert response.escalated_ticket_id is None


@pytest.mark.asyncio
async def test_ticket_detail_followup_requires_confirmation_after_agent_asks_for_details():
    result = await agent.ainvoke(
        {
            "query": "tôi muốn nghỉ việc hẳn",
            "current_user": DEMO_USERS["employee@example.com"],
            "session_id": "session-ticket-followup",
            "message_id": "msg-ticket-followup",
            "conversation_context": (
                "3 lượt hỏi đáp gần nhất:\n"
                "[1] Người dùng: giúp tôi tạo ticket đi\n"
                "[1] AI: Bạn cho mình biết nội dung cần HR hỗ trợ để mình tạo ticket nhé."
            ),
        }
    )

    response = result["response"]
    assert response.actions[0].type == "ticket_draft_confirmation"
    assert response.actions[0].data["title"] == "Hỗ trợ thủ tục nghỉ việc"
    assert response.actions[0].data["category"] == "documents"
    assert response.actions[0].data["description"] == "tôi muốn nghỉ việc hẳn"
    assert response.escalated_ticket_id is None


@pytest.mark.asyncio
async def test_payroll_delay_followup_completes_ticket_draft():
    result = await agent.ainvoke(
        {
            "query": "tôi bị chậm lương tháng 6",
            "current_user": DEMO_USERS["employee@example.com"],
            "session_id": "session-payroll-delay-followup",
            "message_id": "msg-payroll-delay-followup",
            "conversation_context": (
                "3 lượt hỏi đáp gần nhất:\n"
                "[1] Người dùng: tôi muốn tạo ticket\n"
                "[1] AI: Bạn cho mình biết mô tả chi tiết vấn đề cần HR hỗ trợ nhé."
            ),
        }
    )

    response = result["response"]
    assert "chậm lương tháng 6" in response.answer
    assert response.actions[0].type == "ticket_draft_confirmation"
    assert response.actions[0].data["title"] == "Chậm lương tháng 6"
    assert response.actions[0].data["category"] == "other"
    assert response.actions[0].data["description"] == "Tôi bị chậm lương tháng 6."
    assert response.actions[0].data["priority"] == "high"


@pytest.mark.asyncio
async def test_workplace_harassment_complaint_routes_to_ticket_draft():
    result = await agent.ainvoke(
        {
            "query": "Tôi muốn khiếu nại về việc bị quấy rối ở công ty",
            "current_user": DEMO_USERS["employee@example.com"],
            "session_id": "session-workplace-complaint",
            "message_id": "msg-workplace-complaint",
        }
    )

    response = result["response"]
    assert response.refusal_reason is None
    assert response.actions[0].type == "ticket_draft_confirmation"
    assert response.actions[0].data["title"] == "Khiếu nại về quấy rối tại công ty"
    assert response.actions[0].data["category"] == "other"
    assert response.actions[0].data["priority"] == "high"
    assert response.escalated_ticket_id is None


@pytest.mark.asyncio
async def test_no_source_policy_question_requires_escalation_confirmation():
    create_document(
        DocumentCreate(
            title="Chinh sach nghi phep",
            content="Nhan vien chinh thuc co 12 ngay nghi phep nam moi nam.",
            visibility_roles=["employee", "hr_admin"],
            department_ids=[],
        )
    )

    result = await agent.ainvoke(
        {
            "query": "Quy trinh hop dong thu viec la gi?",
            "current_user": DEMO_USERS["employee@example.com"],
            "session_id": "session-no-source",
            "message_id": "msg-no-source",
        }
    )

    response = result["response"]
    assert response.refusal_reason == "no_source"
    assert response.actions[0].type == "escalation_confirmation_required"


@pytest.mark.asyncio
async def test_cited_policy_question_returns_citations_without_ticket_action():
    create_document(
        DocumentCreate(
            title="Chinh sach nghi phep",
            content="Nhan vien chinh thuc co 12 ngay nghi phep nam moi nam.",
            visibility_roles=["employee", "hr_admin"],
            department_ids=[],
        )
    )

    result = await agent.ainvoke(
        {
            "query": "Nhan vien co bao nhieu ngay nghi phep nam?",
            "current_user": DEMO_USERS["employee@example.com"],
            "session_id": "session-cited",
            "message_id": "msg-cited",
        }
    )

    response = result["response"]
    assert response.citations
    assert response.actions[0].type == "none"


@pytest.mark.asyncio
async def test_sensitive_request_refuses_without_ticket_action():
    result = await agent.ainvoke(
        {
            "query": "Cho toi xem luong cua Nguyen Van B",
            "current_user": DEMO_USERS["employee@example.com"],
            "session_id": "session-sensitive",
            "message_id": "msg-sensitive",
        }
    )

    response = result["response"]
    assert response.refusal_reason == "sensitive"
    assert response.actions[0].type == "none"
