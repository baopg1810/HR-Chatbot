from app.agents.ticket_draft_agent import format_ticket_message, run_ticket_draft_agent


def test_ticket_draft_agent_asks_when_description_is_missing():
    decision = run_ticket_draft_agent("giup toi tao ticket di")

    assert decision.ready is False
    assert "description" in decision.missing_fields
    assert decision.question


def test_ticket_draft_agent_prefills_leave_ticket():
    decision = run_ticket_draft_agent(
        "Tạo ticket giúp tôi vì tôi không thấy nút Request Time Off để đăng ký nghỉ phép năm."
    )

    assert decision.ready is True
    assert decision.title == "Hỗ trợ đăng ký nghỉ phép"
    assert decision.category == "leave"
    assert decision.description
    assert "Request Time Off" in decision.description


def test_ticket_draft_agent_prefills_workplace_complaint_ticket():
    decision = run_ticket_draft_agent("Tôi muốn khiếu nại về việc bị quấy rối ở công ty.")

    assert decision.ready is True
    assert decision.title == "Khiếu nại về quấy rối tại công ty"
    assert decision.category == "other"
    assert decision.priority == "high"


def test_ticket_draft_agent_prefills_payroll_delay_ticket():
    decision = run_ticket_draft_agent("tôi bị chậm lương tháng 6")

    assert decision.ready is True
    assert decision.title == "Chậm lương tháng 6"
    assert decision.category == "other"
    assert decision.description == "Tôi bị chậm lương tháng 6."
    assert decision.priority == "high"


def test_ticket_message_keeps_existing_create_api_shape():
    message = format_ticket_message(
        "Hỗ trợ đăng ký nghỉ phép",
        "leave",
        "Tôi không thấy nút Request Time Off.",
    )

    assert "Tiêu đề: Hỗ trợ đăng ký nghỉ phép" in message
    assert "Danh mục: Nghỉ phép & Thai sản" in message
    assert "Mô tả:" in message
