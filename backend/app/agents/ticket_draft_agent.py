from __future__ import annotations

import json
import re
import unicodedata
from typing import Literal

from pydantic import BaseModel, Field, ValidationError

from app.services.llm import build_prompt_with_fitted_history, generate_text

TicketDraftCategory = Literal["leave", "benefits", "equipment", "documents", "other"]
TicketDraftPriority = Literal["low", "normal", "high"]
TicketDraftField = Literal["title", "category", "description"]

TICKET_CATEGORY_LABELS: dict[TicketDraftCategory, str] = {
    "leave": "Nghỉ phép & Thai sản",
    "benefits": "Lương & Phúc lợi",
    "equipment": "Thiết bị & IT Support",
    "documents": "Giấy tờ & Thủ tục hành chính",
    "other": "Khác",
}


class TicketDraftDecision(BaseModel):
    ready: bool = False
    title: str | None = None
    category: TicketDraftCategory | None = None
    description: str | None = None
    missing_fields: list[TicketDraftField] = Field(default_factory=list)
    suggested_fields: list[str] = Field(default_factory=list)
    question: str | None = None
    priority: TicketDraftPriority = "normal"


def run_ticket_draft_agent(query: str, conversation_context: str | None = None) -> TicketDraftDecision:
    """Tiny ReAct-style ticket agent: observe context, infer fields, then ask or draft."""

    llm_decision = _draft_with_llm(query, conversation_context)
    if llm_decision is not None:
        return _finalize_decision(query, llm_decision)
    return _draft_with_rules(query)


def format_ticket_message(title: str, category: TicketDraftCategory, description: str) -> str:
    return (
        f"Tiêu đề: {title.strip()}\n"
        f"Danh mục: {TICKET_CATEGORY_LABELS.get(category, TICKET_CATEGORY_LABELS['other'])}\n\n"
        f"Mô tả:\n{description.strip()}"
    )


def _draft_with_llm(query: str, conversation_context: str | None) -> TicketDraftDecision | None:
    generated = generate_text(_build_ticket_draft_prompt(query, conversation_context))
    if not generated:
        return None
    payload = _extract_json_object(generated)
    if payload is None:
        return None
    try:
        return TicketDraftDecision.model_validate(payload)
    except ValidationError:
        return None


def _draft_with_rules(query: str) -> TicketDraftDecision:
    description = _clean_description(query)
    category = _infer_category(description)
    description = _fallback_ticket_description(description, category)
    if _is_payroll_issue(_normalize(description)):
        description = _sentence_case_with_period(description)
    if not _has_concrete_description(description):
        return TicketDraftDecision(
            ready=False,
            missing_fields=["description"],
            suggested_fields=suggest_ticket_details("other", ""),
            question=(
                "Bạn cho mình biết mô tả chi tiết vấn đề cần HR hỗ trợ nhé. "
                "Ví dụ: bạn đang gặp khó khăn gì, liên quan đến chủ đề nào, và mong HR xử lý ra sao?"
            ),
        )

    title = _title_from_description(description, category)
    return TicketDraftDecision(
        ready=True,
        title=title,
        category=category,
        description=description,
        priority=_infer_priority(description),
        missing_fields=[],
        suggested_fields=suggest_ticket_details(category, description),
        question=None,
    )


def _finalize_decision(query: str, decision: TicketDraftDecision) -> TicketDraftDecision:
    query_description = _clean_description(query)
    llm_description = _clean_rewritten_description(decision.description) or _clean_description(decision.description or "")
    use_llm_description = False
    if _is_payroll_issue(_normalize(query_description)):
        description = query_description
    elif _has_concrete_description(llm_description):
        description = llm_description
        use_llm_description = True
    else:
        description = query_description
    category = decision.category or _infer_category(description)
    if not use_llm_description:
        description = _fallback_ticket_description(description, category)
    if _is_payroll_issue(_normalize(description)):
        description = _sentence_case_with_period(description)
    if not _has_concrete_description(description):
        missing = decision.missing_fields or ["description"]
        return TicketDraftDecision(
            ready=False,
            missing_fields=list(dict.fromkeys(missing)),
            suggested_fields=suggest_ticket_details("other", ""),
            question=(
                "Bạn cho mình biết mô tả chi tiết vấn đề cần HR hỗ trợ nhé. "
                "Mình sẽ dùng thông tin đó để điền form ticket."
            ),
        )

    category = _infer_category(description)
    title = _title_from_description(description, category)
    return TicketDraftDecision(
        ready=True,
        title=title,
        category=category,
        description=description,
        priority=decision.priority or _infer_priority(description),
        missing_fields=[],
        suggested_fields=suggest_ticket_details(category, description),
        question=None,
    )


def _build_ticket_draft_prompt(query: str, conversation_context: str | None) -> str:
    categories = "\n".join(f"- {key}: {label}" for key, label in TICKET_CATEGORY_LABELS.items())

    def render(history: str) -> str:
        history_block = f"LỊCH SỬ HỘI THOẠI:\n{history}\n\n" if history else ""
        return (
            "Bạn là một ReAct-style agent nhỏ chuyên chuẩn bị ticket HR cho nhân viên.\n"
            "Nhiệm vụ: quan sát tin nhắn mới nhất và lịch sử gần đây, trích xuất form ticket nếu đủ thông tin.\n"
            "Không tạo ticket thật. Không bịa chi tiết cụ thể chưa có trong tin nhắn.\n"
            "Bạn được phép tự viết tiêu đề ngắn, chọn danh mục phù hợp và viết lại description thành 1 đoạn ngắn, tự nhiên nếu mô tả vấn đề đã rõ.\n"
            "Description không được lặp lại các cụm như 'tạo ticket', 'mở ticket', 'gửi yêu cầu' nếu đó chỉ là ý định thao tác.\n"
            "Nếu chưa có mô tả vấn đề cụ thể, hãy hỏi lại đúng thông tin còn thiếu.\n\n"
            "Danh mục hợp lệ:\n"
            f"{categories}\n\n"
            "Trả về duy nhất JSON hợp lệ theo schema:\n"
            "{\n"
            '  "ready": true,\n'
            '  "title": "string hoặc null",\n'
            '  "category": "leave|benefits|equipment|documents|other hoặc null",\n'
            '  "description": "string hoặc null",\n'
            '  "missing_fields": ["title|category|description"],\n'
            '  "question": "câu hỏi tiếng Việt để hỏi lại hoặc null",\n'
            '  "priority": "low|normal|high"\n'
            "}\n\n"
            f"{history_block}"
            f"TIN NHẮN MỚI NHẤT:\n{query}\n"
        )

    return build_prompt_with_fitted_history(conversation_context, render)


def _extract_json_object(text: str) -> dict | None:
    stripped = text.strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", stripped, flags=re.DOTALL | re.IGNORECASE)
    candidate = fenced.group(1) if fenced else stripped
    if not candidate.startswith("{"):
        start = candidate.find("{")
        end = candidate.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return None
        candidate = candidate[start : end + 1]
    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _clean_title(value: str | None) -> str | None:
    if not value:
        return None
    title = _compact(value).strip(" .:-")
    if not title:
        return None
    return title[:120].rstrip()


def _clean_description(value: str | None) -> str:
    if not value:
        return ""
    cleaned = _compact(value).strip()
    cleaned = re.sub(
        r"^\s*(tôi|toi|mình|minh|em|anh|chị|chi)?\s*(muốn|muon|cần|can|xin|vui\s+lòng|vui\s+long)?\s*"
        r"(tạo|tao|mở|mo|gửi|gui|lập|lap)\s+(ticket|phiếu|phieu|yêu cầu|yeu cau)\s*"
        r"(giúp tôi|giup toi|cho tôi|cho toi|giúp mình|giup minh|cho mình|cho minh)?\s*",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(r"^\s*(tạo|tao|mở|mo|gửi|gui|lập|lap)\s+(ticket|phiếu|phieu|yêu cầu|yeu cau)\s*(giúp tôi|giup toi|cho tôi|cho toi)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"^\s*(giúp tôi|giup toi|cho tôi|cho toi)\s+(tạo|tao|mở|mo|gửi|gui|lập|lap)\s+(ticket|phiếu|phieu|yêu cầu|yeu cau)\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"^\s*(về việc|ve viec|về|ve)\s+", "", cleaned, flags=re.IGNORECASE)
    return cleaned.strip(" .")


def rewrite_ticket_description(
    current_description: str,
    new_detail: str,
    category: TicketDraftCategory | None = None,
) -> str:
    current = _clean_description(current_description)
    detail = _clean_description(new_detail)
    if not detail:
        return current
    if current and _normalize(detail) in _normalize(current):
        return current

    generated = generate_text(_build_description_rewrite_prompt(current, detail, category))
    rewritten = _clean_rewritten_description(generated)
    if rewritten:
        return rewritten

    combined = " ".join(part for part in [current.rstrip(".!?"), detail] if part)
    return _fallback_ticket_description(combined, category)


def _build_description_rewrite_prompt(
    current_description: str,
    new_detail: str,
    category: TicketDraftCategory | None,
) -> str:
    category_label = TICKET_CATEGORY_LABELS.get(category or "other", TICKET_CATEGORY_LABELS["other"])
    return (
        "Bạn là trợ lý HR đang biên tập mô tả ticket.\n"
        "Hãy viết lại thành đúng 1 đoạn tiếng Việt ngắn, tự nhiên, đủ ý từ mô tả hiện tại và thông tin mới.\n"
        "Không bịa thêm ngày, người, số liệu hoặc chi tiết chưa được cung cấp.\n"
        "Không dùng bullet, markdown, lời chào, hoặc các cụm 'tạo ticket', 'mở ticket', 'gửi yêu cầu' nếu chỉ là thao tác.\n\n"
        f"Danh mục: {category_label}\n"
        f"Mô tả hiện tại: {current_description or '(trống)'}\n"
        f"Thông tin mới: {new_detail}\n\n"
        "Chỉ trả về đoạn mô tả."
    )


def _clean_rewritten_description(value: str | None) -> str:
    if not value:
        return ""
    cleaned = _compact(value).strip(" `\"'")
    cleaned = re.sub(r"^mô\s+tả\s*:\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*\n+\s*", " ", cleaned)
    if not _has_concrete_description(cleaned):
        return ""
    return cleaned[:800].strip()


def _fallback_ticket_description(description: str, category: TicketDraftCategory | None = None) -> str:
    cleaned = _clean_description(description)
    if not cleaned:
        return ""
    normalized = _normalize(cleaned)
    if category == "leave" and normalized in {"xin nghi phep", "nghi phep", "dang ky nghi phep", "xin dang ky nghi phep"}:
        return "Tôi muốn đăng ký nghỉ phép."
    return cleaned


def _has_concrete_description(value: str) -> bool:
    normalized = _normalize(value)
    removable_patterns = [
        r"\b(toi|minh|em|anh|chi|ban)\b",
        r"\b(muon|can|hay|vui\s+long|giup|giup\s+toi|cho\s+toi)\b",
        r"\b(tao|mo|gui|lap)\b",
        r"\b(ticket|phieu|yeu\s+cau|ho\s+tro|hr|nhan\s+su)\b",
        r"\b(ve|cho|den|voi)\b",
    ]
    remaining = normalized
    for pattern in removable_patterns:
        remaining = re.sub(pattern, " ", remaining)
    meaningful_tokens = re.findall(r"[a-z0-9]{2,}", remaining)
    return len(meaningful_tokens) >= 3


def _infer_category(description: str) -> TicketDraftCategory:
    normalized = _normalize(description)
    if _is_payroll_issue(normalized):
        return "other"
    if re.search(
        r"\b(khieu\s+nai|phan\s+anh|to\s+cao|quay\s+roi|harassment|complaint|report|bat\s+nat|bullying|ky\s+thi|discrimination|phan\s+biet\s+doi\s+xu|tra\s+dua|retaliation|misconduct)\b",
        normalized,
    ):
        return "other"
    if re.search(r"\b(nghi\s+phep|ngay\s+phep|phep\s+nam|thai\s+san|time\s+off|request\s+time\s+off)\b", normalized):
        return "leave"
    if re.search(r"\b(luong|phuc\s+loi|bao\s+hiem|thuong|payroll|benefit|salary|bonus)\b", normalized):
        return "benefits"
    if re.search(r"\b(thiet\s+bi|laptop|may\s+tinh|it|tai\s+khoan|dang\s+nhap|truy\s+cap|password|mat\s+khau)\b", normalized):
        return "equipment"
    if re.search(r"\b(hop\s+dong|ho\s+so|giay\s+to|thu\s+tuc|xac\s+nhan|onboarding|offboarding|nghi\s+viec)\b", normalized):
        return "documents"
    return "other"


def suggest_ticket_details(category: TicketDraftCategory | None, description: str = "") -> list[str]:
    normalized = _normalize(description)
    if category == "leave":
        suggestions = [
            "Ngày hoặc buổi nghỉ cụ thể",
            "Lý do nghỉ và loại nghỉ nếu có",
            "Bạn đã báo quản lý trực tiếp chưa",
            "Người hoặc đầu việc sẽ bàn giao trong thời gian nghỉ",
        ]
    elif category == "benefits":
        suggestions = [
            "Kỳ lương, phúc lợi hoặc bảo hiểm liên quan",
            "Số tiền/trạng thái bạn thấy chưa đúng nếu có",
            "Ảnh chụp payslip, thông báo hoặc email liên quan",
            "Mong muốn HR kiểm tra hoặc điều chỉnh điều gì",
        ]
    elif category == "equipment":
        suggestions = [
            "Thiết bị, tài khoản hoặc hệ thống đang gặp vấn đề",
            "Thông báo lỗi hoặc ảnh chụp màn hình nếu có",
            "Thời điểm bắt đầu và mức độ ảnh hưởng công việc",
            "Bạn cần cấp mới, sửa lỗi hay mở quyền truy cập",
        ]
    elif category == "documents":
        suggestions = [
            "Loại giấy tờ hoặc thủ tục cần HR hỗ trợ",
            "Mốc thời gian hoặc hạn xử lý mong muốn",
            "Phòng ban/người liên quan nếu có",
            "File, email hoặc thông tin tham chiếu liên quan",
        ]
    else:
        suggestions = [
            "Vấn đề hoặc yêu cầu cụ thể cần HR xử lý",
            "Thời gian, địa điểm hoặc người liên quan nếu có",
            "Tác động hiện tại đến công việc của bạn",
            "Mong muốn HR hỗ trợ theo hướng nào",
        ]

    if "anh chup" in normalized or "hinh anh" in normalized or "screenshot" in normalized:
        suggestions = [item for item in suggestions if "ảnh" not in item.lower()]
    return suggestions


def _infer_priority(description: str) -> TicketDraftPriority:
    normalized = _normalize(description)
    if _is_payroll_issue(normalized):
        return "high"
    if re.search(
        r"\b(khan\s+cap|gap|urgent|ngay\s+lap\s+tuc|bi\s+khoa|khong\s+truy\s+cap|quay\s+roi|harassment|bat\s+nat|bullying|ky\s+thi|discrimination|phan\s+biet\s+doi\s+xu|tra\s+dua|retaliation|misconduct)\b",
        normalized,
    ):
        return "high"
    return "normal"


def _title_from_description(description: str, category: TicketDraftCategory) -> str:
    normalized = _normalize(description)
    if _is_payroll_delay(normalized):
        month = _payroll_month(normalized)
        return f"Chậm lương tháng {month}" if month else "Vấn đề về lương"
    if _is_payroll_issue(normalized):
        return "Vấn đề về lương"
    if "quay roi" in normalized or "harassment" in normalized:
        return "Khiếu nại về quấy rối tại công ty"
    if "bat nat" in normalized or "bullying" in normalized:
        return "Khiếu nại về bắt nạt tại nơi làm việc"
    if any(term in normalized for term in {"ky thi", "discrimination", "phan biet doi xu"}):
        return "Khiếu nại về phân biệt đối xử"
    if "tra dua" in normalized or "retaliation" in normalized:
        return "Khiếu nại về trả đũa tại nơi làm việc"
    if any(term in normalized for term in {"khieu nai", "phan anh", "to cao", "complaint", "report"}):
        return "Khiếu nại HR"
    if "request time off" in normalized or "nghi phep" in normalized or "phep nam" in normalized:
        return "Hỗ trợ đăng ký nghỉ phép"
    if "hop dong" in normalized:
        return "Hỗ trợ xử lý hợp đồng"
    if "nghi viec" in normalized:
        return "Hỗ trợ thủ tục nghỉ việc"
    if "bao hiem" in normalized:
        return "Hỗ trợ thông tin bảo hiểm"
    if category == "equipment":
        return "Hỗ trợ truy cập hoặc thiết bị"
    words = _compact(description).split()
    summary = " ".join(words[:10]).strip(" .")
    if not summary:
        return "Yêu cầu hỗ trợ HR"
    return summary[:1].upper() + summary[1:120]


def _is_payroll_issue(normalized: str) -> bool:
    return bool(
        re.search(
            r"\b(cham\s+luong|tre\s+luong|chua\s+nhan(?:\s+duoc)?\s+luong|thieu\s+luong|sai\s+luong|luong\s+thang|payroll\s+issue|salary\s+delay|salary\s+missing|payslip|tax\s+deduction|insurance\s+deduction)\b",
            normalized,
        )
    )


def _is_payroll_delay(normalized: str) -> bool:
    return bool(re.search(r"\b(cham\s+luong|tre\s+luong|chua\s+nhan(?:\s+duoc)?\s+luong|salary\s+delay|salary\s+missing)\b", normalized))


def _payroll_month(normalized: str) -> str | None:
    match = re.search(r"\bthang\s+([0-9]{1,2})\b", normalized)
    if match:
        return match.group(1)
    return None


def _sentence_case_with_period(value: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        return cleaned
    cleaned = cleaned[:1].upper() + cleaned[1:]
    if cleaned[-1] not in ".!?":
        cleaned += "."
    return cleaned


def _compact(value: str) -> str:
    return re.sub(r"\s+", " ", str(value)).strip()


def _normalize(message: str) -> str:
    normalized = unicodedata.normalize("NFKD", message.lower().replace("đ", "d").replace("Đ", "D"))
    ascii_text = "".join(char for char in normalized if not unicodedata.combining(char))
    ascii_text = re.sub(r"[^a-z0-9\s]", " ", ascii_text)
    return re.sub(r"\s+", " ", ascii_text).strip()
