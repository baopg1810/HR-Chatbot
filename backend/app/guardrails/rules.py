from __future__ import annotations

import re
import unicodedata

from app.guardrails.messages import (
    AMBIGUOUS_MESSAGE,
    GENERAL_SAFETY_MESSAGE,
    OUT_OF_SCOPE_MESSAGE,
    PROMPT_INJECTION_MESSAGE,
    SENSITIVE_DATA_MESSAGE,
    WORKPLACE_MISCONDUCT_MESSAGE,
)
from app.guardrails.schemas import (
    GuardrailDecision,
    InputSafeguardDecision,
    OutputSafeguardDecision,
    RefusalReason,
    ToolGuardrailDecision,
    TopicScopeDecision,
)


HR_TERMS = {
    "hr",
    "nhan",
    "su",
    "nhan su",
    "nhan vien",
    "nghi",
    "phep",
    "nghi phep",
    "luong",
    "thuong",
    "cham luong",
    "tre luong",
    "thieu luong",
    "sai luong",
    "chua nhan luong",
    "payroll",
    "salary",
    "payslip",
    "deduction",
    "tax",
    "bao hiem",
    "bhxh",
    "bhyt",
    "hop dong",
    "cham cong",
    "phuc loi",
    "quyen loi",
    "quy trinh",
    "chinh sach",
    "noi bo",
    "hanh chinh",
    "thiet bi",
    "laptop",
    "may tinh",
    "it support",
    "thu viec",
    "thai san",
    "khen thuong",
    "ky luat",
    "dong phuc",
    "phu cap",
    "nghi om",
    "onboarding",
    "offboarding",
    "ticket",
    "helpdesk",
    "khieu nai",
    "phan anh",
    "to cao",
    "quay roi",
    "bat nat",
    "tra dua",
    "phan biet doi xu",
    "misconduct",
    "retaliation",
    "bullying",
    "discrimination",
    "workplace complaint",
    "harassment",
    "complaint",
}

JAILBREAK_PATTERNS = [
    r"\bignore\s+(all\s+)?previous\b",
    r"\bignore\s+(the\s+)?(system|developer)\b",
    r"\bsystem\s+prompt\b",
    r"\bdeveloper\s+message\b",
    r"\bjailbreak\b",
    r"\bprompt\s+injection\b",
    r"\breveal\b.*\b(system|developer)\b",
    r"\bbo\s+qua\b.*\b(huong\s+dan|chi\s+dan|instruction|quy\s+tac)\b",
    r"\bquen\b.*\b(tat\s+ca|cac)\b.*\b(chi\s+dan|huong\s+dan)\b",
    r"\bin\b.*\b(system\s+prompt|prompt\s+he\s+thong)\b",
    r"\btiet\s+lo\b.*\b(system\s+prompt|prompt\s+he\s+thong|chi\s+dan)\b",
    r"\bdong\s+vai\b.*\b(khong\s+bi\s+rang\s+buoc|bo\s+qua\s+quy\s+tac)\b",
]

OUTSIDE_SCOPE_PATTERNS = [
    r"\b(thoi\s+tiet|du\s+bao\s+thoi\s+tiet|weather)\b",
    r"\b(bitcoin|crypto|gia\s+vang|chung\s+khoan)\b",
    r"\b(bong\s+da|football|ty\s+so|lich\s+thi\s+dau)\b",
    r"\b(nau\s+an|cong\s+thuc\s+nau|recipe)\b",
    r"\b(dat\s+ve|ve\s+may\s+bay|khach\s+san|du\s+lich)\b",
    r"\b(viet\s+code|debug\s+code|lap\s+trinh|fastapi|python|javascript)\b",
    r"\b(homework|bai\s+tap|giai\s+toan|lich\s+su|dia\s+ly)\b",
]

EXPLICIT_OUTSIDE_SCOPE_TASK_PATTERNS = [
    r"\b(viet|tao|xay\s+dung|debug|sua|giai|huong\s+dan|lam)\b.{0,80}\b(code|script|chuong\s+trinh|api|fastapi|python|javascript|typescript|react|sql)\b",
    r"\b(code|debug\s+code|viet\s+code)\s+(cho|giup|ho|dum|toi|minh|em|anh|chi)\b",
    r"\b(thuat\s+toan|algorithm|quicksort|merge\s*sort|binary\s+search)\b",
    r"\b(du\s+bao\s+thoi\s+tiet|thoi\s+tiet|weather)\b",
    r"\b(bitcoin|crypto|gia\s+vang|chung\s+khoan)\b",
    r"\b(bong\s+da|football|ty\s+so|lich\s+thi\s+dau)\b",
    r"\b(nau\s+an|cong\s+thuc\s+nau|recipe)\b",
    r"\b(homework|bai\s+tap|giai\s+toan|lich\s+su|dia\s+ly)\b",
]

SENSITIVE_FIELD_PATTERNS = [
    r"\b(luong|thu\s+nhap|salary|payroll|bang\s+luong)\b",
    r"\b(bao\s+hiem|bhxh|bhyt|insurance)\b",
    r"\b(thong\s+tin\s+ca\s+nhan|ho\s+so\s+nhan\s+su|personal\s+data)\b",
    r"\b(so\s+tai\s+khoan|tai\s+khoan\s+ngan\s+hang|bank\s+account)\b",
    r"\b(can\s+cuoc|cccd|cmnd|passport|ho\s+chieu)\b",
    r"\b(mat\s+khau|password|otp|ma\s+xac\s+thuc)\b",
    r"\b(dia\s+chi\s+nha|so\s+dien\s+thoai\s+ca\s+nhan|email\s+ca\s+nhan)\b",
]

PERSONAL_HR_METRIC_PATTERNS = [
    r"\b(ngay\s+phep|nghi\s+phep|phep\s+nam|leave)\b.{0,40}\b(con\s+lai|remaining|balance|status)\b",
    r"\b(con\s+lai|remaining|balance|status)\b.{0,40}\b(ngay\s+phep|nghi\s+phep|phep\s+nam|leave)\b",
    r"\b(trang\s+thai|status)\b.{0,40}\b(bao\s+hiem|insurance|khen\s+thuong|xet\s+duyet|reward|review)\b",
    r"\b(bao\s+hiem|insurance|khen\s+thuong|xet\s+duyet|reward|review)\b.{0,40}\b(trang\s+thai|status)\b",
]

THIRD_PARTY_PATTERNS = [
    r"\b(cua|cau|cho|ve|xem)\s+(nguyen|tran|le|pham|hoang|huynh|phan|vu|vo|dang|bui|do|ho|ngo|duong)\b",
    r"\b(cua|cau|cho|ve)\s+(anh|chi|ban|dong\s+nghiep|nhan\s+vien)\s+[a-z0-9]",
    r"\bnguoi\s+khac\b",
    r"\bdong\s+nghiep\b",
    r"\bnhan\s+vien\s+khac\b",
    r"\b[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}\b",
]

SELF_PATTERNS = [
    r"\b(cua|ve)\s+(toi|minh|em|anh|chi|ban\s+than)\b",
    r"\b(toi|minh|em)\s+(co|con|duoc|da|bi|gap|chua|khong|can|muon)\b",
    r"\b(my|mine|myself)\b",
]

PII_PATTERNS = [
    r"\b[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}\b",
    r"\b(?:\+?84|0)(?:\d[\s.-]?){8,10}\b",
    r"\b\d{9,12}\b",
]


def evaluate_chat_guardrails(message: str) -> GuardrailDecision:
    return _evaluate_rule_guardrails(message)


def looks_like_hr_question(message: str) -> bool:
    normalized = _normalize(message)
    tokens = set(_tokens(normalized))
    if tokens.intersection({term for term in HR_TERMS if " " not in term}):
        return True
    return any(term in normalized for term in HR_TERMS if " " in term)


def is_low_risk_self_service_or_helpdesk(message: str) -> bool:
    normalized = _normalize(message)
    return (
        _is_helpdesk_usage_message(normalized)
        or _is_low_risk_hr_policy_question(normalized)
        or _is_self_service_hr_request(normalized)
        or _is_workplace_report(normalized)
        or _is_own_payroll_issue(normalized)
    )


def is_workplace_misconduct_report(message: str) -> bool:
    return _is_workplace_report(_normalize(message))


def rule_input_safeguard(message: str) -> InputSafeguardDecision:
    normalized = _normalize(message)
    if _matches_any(normalized, JAILBREAK_PATTERNS):
        return InputSafeguardDecision(
            allowed=False,
            blocked=True,
            action="block",
            risk_level="high",
            user_message=PROMPT_INJECTION_MESSAGE,
            internal_reason="rule_jailbreak",
            reason_code="jailbreak",
        )
    if _is_workplace_report(normalized):
        return InputSafeguardDecision(
            allowed=True,
            blocked=False,
            requires_handoff=True,
            action="handoff",
            risk_level="medium",
            user_message=WORKPLACE_MISCONDUCT_MESSAGE,
            internal_reason="workplace_misconduct_report_requires_confidential_hr_handling",
            reason_code="workplace_misconduct",
        )
    if _is_own_payroll_issue(normalized):
        return InputSafeguardDecision(
            allowed=True,
            blocked=False,
            requires_handoff=False,
            action="allow",
            risk_level="low",
            user_message="",
            internal_reason="own_payroll_issue_allow",
            reason_code="allow",
        )

    decision = _evaluate_rule_guardrails(message)
    if decision.allowed:
        return InputSafeguardDecision(
            allowed=True,
            action="allow",
            user_message="",
            internal_reason="rule_allow",
            reason_code="allow",
        )
    reason = decision.refusal_reason or "outside_scope"
    return InputSafeguardDecision(
        allowed=False,
        blocked=True,
        action="block",
        risk_level="high" if reason in {"jailbreak", "sensitive"} else "medium",
        user_message=_message_for_reason(reason),
        internal_reason=f"rule_{reason}",
        reason_code=reason,
    )


def rule_topic_scope(message: str) -> TopicScopeDecision:
    normalized = _normalize(message)
    if _is_workplace_report(normalized):
        return TopicScopeDecision(
            scope="in_scope",
            topic=_workplace_report_topic(normalized),
            sensitivity="confidential",
            confidence=0.9,
            user_message=WORKPLACE_MISCONDUCT_MESSAGE,
            internal_reason="workplace_misconduct_report_in_scope",
        )
    if _is_own_payroll_issue(normalized):
        return TopicScopeDecision(
            scope="in_scope",
            topic=_payroll_issue_topic(normalized),
            sensitivity="sensitive",
            confidence=0.9,
            user_message="Mình có thể hỗ trợ bạn tạo ticket về vấn đề lương.",
            internal_reason="own_payroll_issue_in_scope",
        )
    if _is_helpdesk_usage_message(normalized):
        return TopicScopeDecision(
            scope="in_scope",
            topic="hr_helpdesk_usage",
            sensitivity="normal",
            confidence=0.82,
            user_message="",
            internal_reason="helpdesk_usage_message",
        )
    if _is_ambiguous_hr_question(normalized):
        return TopicScopeDecision(
            scope="ambiguous",
            topic="low_specificity_hr",
            sensitivity="normal",
            confidence=0.55,
            user_message=AMBIGUOUS_MESSAGE,
            internal_reason="short_low_specificity_hr_message",
        )
    if _is_outside_scope(normalized) or not looks_like_hr_question(normalized):
        return TopicScopeDecision(
            scope="out_of_scope",
            topic="non_hr",
            sensitivity="normal",
            confidence=0.9 if _is_outside_scope(normalized) else 0.78,
            user_message=OUT_OF_SCOPE_MESSAGE,
            internal_reason="rule_outside_scope",
        )

    sensitivity = "normal"
    if _matches_any(normalized, SENSITIVE_FIELD_PATTERNS):
        sensitivity = "confidential" if _is_third_party_sensitive_request(normalized) else "sensitive"

    return TopicScopeDecision(
        scope="in_scope",
        topic=_infer_topic(normalized),
        sensitivity=sensitivity,
        confidence=0.86,
        user_message="",
        internal_reason="rule_in_scope",
    )


def rule_output_safeguard(
    draft_answer: str,
    *,
    user_message: str = "",
    context_summary: str = "",
    has_citations: bool = False,
    has_tool_result: bool = False,
    topic: str = "",
) -> OutputSafeguardDecision:
    if _is_known_safe_guardrail_fallback(draft_answer):
        return OutputSafeguardDecision(
            allowed=True,
            action="allow",
            risk_level="none",
            user_message="",
            redacted_text=None,
            internal_reason="known_safe_guardrail_fallback",
        )

    normalized_answer = _normalize(draft_answer)
    if _matches_any(normalized_answer, JAILBREAK_PATTERNS) or re.search(
        r"\b(system\s+prompt|developer\s+message|internal\s+tool\s+schema|api\s+key|secret)\b",
        normalized_answer,
    ):
        return OutputSafeguardDecision(
            allowed=False,
            action="block",
            risk_level="high",
            user_message=GENERAL_SAFETY_MESSAGE,
            redacted_text=None,
            internal_reason="output_reveals_internal_instructions",
        )

    if _matches_any(draft_answer.lower(), PII_PATTERNS):
        redacted = _redact_pii(draft_answer)
        return OutputSafeguardDecision(
            allowed=False,
            action="redact",
            risk_level="medium",
            user_message=SENSITIVE_DATA_MESSAGE,
            redacted_text=redacted,
            internal_reason="output_contains_pii",
        )

    if user_message and _is_sensitive_data_request(_normalize(user_message)):
        return OutputSafeguardDecision(
            allowed=False,
            action="fallback",
            risk_level="high",
            user_message=SENSITIVE_DATA_MESSAGE,
            redacted_text=None,
            internal_reason="output_for_sensitive_request",
        )

    if user_message and _is_outside_scope(_normalize(user_message)):
        return OutputSafeguardDecision(
            allowed=False,
            action="fallback",
            risk_level="medium",
            user_message=OUT_OF_SCOPE_MESSAGE,
            redacted_text=None,
            internal_reason="output_for_out_of_scope_request",
        )

    if _looks_like_unsupported_policy_claim(
        normalized_answer,
        has_citations=has_citations,
        context_summary=context_summary,
        has_tool_result=has_tool_result,
        topic=topic,
    ):
        return OutputSafeguardDecision(
            allowed=False,
            action="fallback",
            risk_level="medium",
            user_message="Mình chưa có đủ nguồn HR đáng tin cậy để khẳng định chính sách này. Bạn vui lòng kiểm tra lại tài liệu nội bộ hoặc liên hệ HR phụ trách.",
            redacted_text=None,
            internal_reason="unsupported_policy_claim",
        )

    return OutputSafeguardDecision(
        allowed=True,
        action="allow",
        risk_level="none",
        user_message="",
        redacted_text=None,
        internal_reason="rule_allow",
    )


def rule_tool_guardrail(tool_name: str, user: object | None = None, *, side_effect: bool = False) -> ToolGuardrailDecision:
    if user is None:
        return ToolGuardrailDecision(
            allowed=False,
            action="require_auth",
            tool_name=tool_name,
            risk_level="medium",
            user_message=SENSITIVE_DATA_MESSAGE,
            internal_reason="tool_requires_authenticated_user",
        )
    if tool_name in {"salary_lookup", "employee_record_lookup"} and getattr(user, "role", "") not in {"hr_admin", "admin"}:
        return ToolGuardrailDecision(
            allowed=False,
            action="handoff",
            tool_name=tool_name,
            risk_level="high",
            user_message=SENSITIVE_DATA_MESSAGE,
            internal_reason="user_lacks_permission_for_confidential_tool",
        )
    if side_effect:
        return ToolGuardrailDecision(
            allowed=True,
            action="require_confirmation",
            tool_name=tool_name,
            risk_level="medium",
            user_message="Bạn vui lòng xác nhận trước khi mình gửi yêu cầu này cho HR.",
            internal_reason="side_effect_tool_requires_confirmation",
        )
    return ToolGuardrailDecision(
        allowed=True,
        action="allow",
        tool_name=tool_name,
        risk_level="low",
        user_message="",
        internal_reason="tool_allow",
    )


def _evaluate_rule_guardrails(message: str) -> GuardrailDecision:
    normalized = _normalize(message)
    if _matches_any(normalized, JAILBREAK_PATTERNS):
        return GuardrailDecision(allowed=False, refusal_reason="jailbreak")
    if _is_sensitive_data_request(normalized):
        return GuardrailDecision(allowed=False, refusal_reason="sensitive")
    if _is_outside_scope(normalized):
        return GuardrailDecision(allowed=False, refusal_reason="outside_scope")
    return GuardrailDecision(allowed=True)


def _is_sensitive_data_request(normalized: str) -> bool:
    has_sensitive_field = _matches_any(normalized, SENSITIVE_FIELD_PATTERNS)
    has_personal_metric_field = _matches_any(normalized, PERSONAL_HR_METRIC_PATTERNS)
    if has_personal_metric_field and _is_third_party_sensitive_request(normalized):
        return True
    if not has_sensitive_field:
        return False
    always_sensitive = _matches_any(
        normalized,
        [
            r"\b(mat\s+khau|password|otp|ma\s+xac\s+thuc)\b",
            r"\b(can\s+cuoc|cccd|cmnd|passport|ho\s+chieu|so\s+tai\s+khoan)\b",
        ],
    )
    if always_sensitive:
        return True
    if _matches_any(normalized, SELF_PATTERNS):
        return False
    return _is_third_party_sensitive_request(normalized)


def _is_third_party_sensitive_request(normalized: str) -> bool:
    return _matches_any(normalized, THIRD_PARTY_PATTERNS) or _has_named_sensitive_target(normalized)


def _has_named_sensitive_target(normalized: str) -> bool:
    non_person_targets = {
        "ban",
        "ban than",
        "bao hiem",
        "chinh",
        "chinh sach",
        "cong",
        "cong ty",
        "eiv",
        "he thong",
        "noi bo",
        "phong",
        "quy",
        "quy dinh",
        "toi",
    }
    non_person_prefixes = {
        "ban than",
        "bao hiem",
        "chinh sach",
        "cong ty",
        "he thong",
        "noi bo",
        "quy dinh",
    }
    ambiguous_non_person_tokens = {"ban", "chinh", "cong", "phong", "quy"}
    field_like_target_tokens = {
        "bang",
        "con",
        "duyet",
        "insurance",
        "khen",
        "leave",
        "luong",
        "ngay",
        "nghi",
        "payroll",
        "phep",
        "review",
        "salary",
        "so",
        "status",
        "thai",
        "thuong",
        "trang",
        "xet",
    }
    vietnamese_name_cues = {
        "nguyen",
        "tran",
        "le",
        "pham",
        "hoang",
        "huynh",
        "phan",
        "vu",
        "vo",
        "dang",
        "bui",
        "do",
        "ho",
        "ngo",
        "duong",
    }

    target_token = r"(?!(?:cua|cau|cho|ve|xem)\b)[a-z0-9]{2,}"
    target_pattern = rf"\b(?:cua|cau|cho|ve|xem)\s+({target_token}(?:\s+{target_token}){{0,3}})"
    for match in re.finditer(target_pattern, normalized):
        target_tokens = match.group(1).split()
        target = " ".join(target_tokens)
        first_token = target_tokens[0]
        if target in non_person_targets:
            continue
        if any(target == prefix or target.startswith(f"{prefix} ") for prefix in non_person_prefixes):
            continue
        if first_token in field_like_target_tokens and not vietnamese_name_cues.intersection(target_tokens[1:]):
            continue
        if first_token in ambiguous_non_person_tokens and not vietnamese_name_cues.intersection(target_tokens[1:]):
            continue
        if first_token in non_person_targets and first_token not in ambiguous_non_person_tokens:
            continue
        return True
    return False


def _is_outside_scope(normalized: str) -> bool:
    if _is_hr_policy_context_for_outside_keyword(normalized):
        return False
    if _matches_any(normalized, EXPLICIT_OUTSIDE_SCOPE_TASK_PATTERNS):
        return True
    if not _matches_any(normalized, OUTSIDE_SCOPE_PATTERNS):
        return False
    return not looks_like_hr_question(normalized)


def _is_hr_policy_context_for_outside_keyword(normalized: str) -> bool:
    if "du lich" not in normalized:
        return False
    return any(
        marker in normalized
        for marker in {
            "chinh sach nghi phep",
            "quy dinh nghi phep",
            "nghi phep khi di du lich",
            "ngay phep",
            "phep nam",
        }
    )


def _is_ambiguous_hr_question(normalized: str) -> bool:
    tokens = _tokens(normalized)
    return len(tokens) <= 6 and any(
        phrase in normalized
        for phrase in {
            "hoi ve quyen loi",
            "hoi ve phuc loi",
            "toi muon hoi ve quyen loi",
            "toi muon hoi ve chinh sach",
        }
    )


def _is_helpdesk_usage_message(normalized: str) -> bool:
    if normalized in {"hello", "hi", "hey", "xin chao", "chao ban", "ban la ai"}:
        return True
    return any(
        re.search(pattern, normalized)
        for pattern in (
            r"\bban\s+(la\s+ai|ten\s+gi)\b",
            r"\bban\s+co\s+the\s+(giup|ho\s+tro|lam)\b",
            r"\bhelpdesk\b",
            r"\bhuong\s+dan\s+su\s+dung\s+(hr|helpdesk)\b",
            r"\b(tao|mo|gui|lap)\s+(ticket|phieu|yeu\s+cau)\b",
            r"\b(ticket|phieu\s+ho\s+tro|yeu\s+cau\s+ho\s+tro)\b",
        )
    )


def _is_low_risk_hr_policy_question(normalized: str) -> bool:
    if _matches_any(normalized, SENSITIVE_FIELD_PATTERNS) or _is_third_party_sensitive_request(normalized):
        return False
    if _is_outside_scope(normalized) or not looks_like_hr_question(normalized):
        return False

    policy_markers = {
        "bao truoc",
        "can bao truoc",
        "chinh sach",
        "ngay phep",
        "nghi phep",
        "phep nam",
        "phuc loi",
        "quy dinh",
        "quy trinh",
        "thu tuc",
    }
    if any(marker in normalized for marker in policy_markers):
        return True
    return bool(
        re.search(r"\b(nhan\s+vien|nguoi\s+lao\s+dong)\b.*\b(duoc|can|phai)\b", normalized)
        and not _matches_any(normalized, SELF_PATTERNS)
    )


def _is_self_service_hr_request(normalized: str) -> bool:
    has_self_reference = _matches_any(normalized, SELF_PATTERNS)
    has_hr_self_service_term = any(
        term in normalized
        for term in {
            "nghi",
            "phep",
            "ngay phep",
            "luong",
            "bao hiem",
            "bhxh",
            "bhyt",
            "hop dong",
            "thuong",
            "cham luong",
            "tre luong",
            "thieu luong",
            "sai luong",
            "chua nhan luong",
            "payroll",
            "salary",
            "payslip",
            "khen thuong",
            "trang thai",
            "con lai",
            "ticket",
            "yeu cau",
            "khieu nai",
            "phan anh",
            "to cao",
            "quay roi",
        }
    )
    return has_self_reference and has_hr_self_service_term


def _is_own_payroll_issue(normalized: str) -> bool:
    has_payroll_issue = _matches_any(
        normalized,
        [
            r"\b(cham\s+luong|tre\s+luong|chua\s+nhan\s+luong|thieu\s+luong|sai\s+luong)\b",
            r"\b(luong\s+thang|luong\s+thang\s+13|bang\s+luong|payslip)\b",
            r"\b(payroll\s+issue|salary\s+delay|salary\s+missing|tax\s+deduction|insurance\s+deduction)\b",
        ],
    )
    if not has_payroll_issue:
        return False
    return _matches_any(normalized, SELF_PATTERNS) or not _is_third_party_sensitive_request(normalized)


def _payroll_issue_topic(normalized: str) -> str:
    if _matches_any(normalized, [r"\b(cham\s+luong|tre\s+luong|chua\s+nhan\s+luong|salary\s+delay|salary\s+missing)\b"]):
        return "payroll_delay_ticket"
    if _matches_any(normalized, [r"\b(thieu\s+luong|sai\s+luong|payroll\s+issue)\b"]):
        return "payroll_issue"
    return "payroll_issue"


def _is_workplace_report(normalized: str) -> bool:
    has_report_term = _matches_any(
        normalized,
        [
            r"\b(khieu\s+nai|phan\s+anh|to\s+cao|complaint|report)\b",
            r"\b(quay\s+roi|harassment|bat\s+nat|bullying|ky\s+thi|discrimination|phan\s+biet\s+doi\s+xu|tra\s+dua|retaliation|misconduct)\b",
        ],
    )
    has_workplace_context = _matches_any(normalized, [r"\b(cong\s+ty|noi\s+bo|noi\s+lam\s+viec|workplace|hr|nhan\s+su)\b"])
    return has_report_term and has_workplace_context


def _workplace_report_topic(normalized: str) -> str:
    if _matches_any(normalized, [r"\b(quay\s+roi|harassment)\b"]):
        return "workplace_harassment_complaint"
    if _matches_any(normalized, [r"\b(bat\s+nat|bullying)\b"]):
        return "bullying_complaint"
    if _matches_any(normalized, [r"\b(ky\s+thi|discrimination|phan\s+biet\s+doi\s+xu)\b"]):
        return "discrimination_complaint"
    if _matches_any(normalized, [r"\b(tra\s+dua|retaliation)\b"]):
        return "retaliation_complaint"
    return "workplace_misconduct"


def _infer_topic(normalized: str) -> str:
    for topic, terms in {
        "leave_policy": {"nghi", "phep", "thai san", "nghi om"},
        "payroll_issue": {"luong", "thuong", "payroll", "thue", "payslip", "cham luong", "tre luong"},
        "insurance": {"bao hiem", "bhxh", "bhyt"},
        "contract": {"hop dong", "thu viec"},
        "ticket": {"ticket", "yeu cau", "helpdesk", "khieu nai", "phan anh", "to cao", "quay roi"},
        "benefits": {"phuc loi", "quyen loi"},
    }.items():
        if any(term in normalized for term in terms):
            return topic
    return "hr_policy"


def _looks_like_unsupported_policy_claim(
    normalized_answer: str,
    *,
    has_citations: bool,
    context_summary: str,
    has_tool_result: bool,
    topic: str,
) -> bool:
    if has_citations or has_tool_result or context_summary.strip() or topic == "hr_helpdesk_usage":
        return False
    has_policy_language = any(term in normalized_answer for term in {"cong ty", "chinh sach", "nhan vien", "nghi"})
    has_strong_claim = any(term in normalized_answer for term in {"chac chan", "bat buoc", "luon", "duoc nghi 30 ngay"})
    return has_policy_language and has_strong_claim


def _redact_pii(text: str) -> str:
    redacted = text
    for pattern in PII_PATTERNS:
        redacted = re.sub(pattern, "[đã ẩn]", redacted, flags=re.IGNORECASE)
    return redacted


def _is_known_safe_guardrail_fallback(text: str) -> bool:
    normalized_text = " ".join(str(text).split())
    return normalized_text in {
        OUT_OF_SCOPE_MESSAGE,
        AMBIGUOUS_MESSAGE,
        SENSITIVE_DATA_MESSAGE,
        PROMPT_INJECTION_MESSAGE,
        GENERAL_SAFETY_MESSAGE,
        "Mình chưa có đủ nguồn HR đáng tin cậy để khẳng định chính sách này. Bạn vui lòng kiểm tra lại tài liệu nội bộ hoặc liên hệ HR phụ trách.",
    }


def _message_for_reason(reason: RefusalReason | str) -> str:
    if reason == "jailbreak":
        return PROMPT_INJECTION_MESSAGE
    if reason == "outside_scope":
        return OUT_OF_SCOPE_MESSAGE
    if reason == "sensitive":
        return SENSITIVE_DATA_MESSAGE
    return GENERAL_SAFETY_MESSAGE


def _matches_any(text: str, patterns: list[str]) -> bool:
    return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns)


def _normalize(message: str) -> str:
    normalized = unicodedata.normalize("NFKD", message.lower().replace("đ", "d").replace("Đ", "D"))
    ascii_text = "".join(char for char in normalized if not unicodedata.combining(char))
    ascii_text = re.sub(r"[^a-z0-9@._%+\-\s]", " ", ascii_text)
    return re.sub(r"\s+", " ", ascii_text).strip()


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]{2,}", text)
