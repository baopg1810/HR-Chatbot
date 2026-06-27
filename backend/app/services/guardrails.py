from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Literal


RefusalReason = Literal["jailbreak", "outside_scope", "sensitive", "no_source"]

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
    "bao hiem",
    "bhxh",
    "bhyt",
    "hop dong",
    "cham cong",
    "phuc loi",
    "quy trinh",
    "chinh sach",
    "noi bo",
    "hanh chinh",
    "thu viec",
    "thai san",
    "khen thuong",
    "ky luat",
    "dong phuc",
    "phu cap",
    "nghi om",
}

JAILBREAK_PATTERNS = [
    r"\bignore\s+(all\s+)?previous\b",
    r"\bignore\s+(the\s+)?(system|developer)\b",
    r"\bsystem\s+prompt\b",
    r"\bdeveloper\s+message\b",
    r"\bjailbreak\b",
    r"\bprompt\s+injection\b",
    r"\breveal\b.*\b(system|developer)\b",
    r"\bbo\s+qua\b.*\b(huong\s+dan|chi\s+dan|quy\s+tac)\b",
    r"\bquen\b.*\b(tat\s+ca|cac)\b.*\b(chi\s+dan|huong\s+dan)\b",
    r"\btiet\s+lo\b.*\b(system\s+prompt|prompt\s+he\s+thong|chi\s+dan)\b",
    r"\bdong\s+vai\b.*\b(khong\s+bi\s+rang\s+buoc|bo\s+qua\s+quy\s+tac)\b",
]

OUTSIDE_SCOPE_PATTERNS = [
    r"\b(thoi\s+tiet|du\s+bao\s+thoi\s+tiet|weather)\b",
    r"\b(bitcoin|crypto|gia\s+vang|chung\s+khoan)\b",
    r"\b(bong\s+da|football|ty\s+so|lich\s+thi\s+dau)\b",
    r"\b(nau\s+an|cong\s+thuc\s+nau|recipe)\b",
    r"\b(dat\s+ve|ve\s+may\s+bay|khach\s+san|du\s+lich)\b",
    r"\b(viet\s+code|debug\s+code|lap\s+trinh)\b",
]

SENSITIVE_FIELD_PATTERNS = [
    r"\b(luong|thu\s+nhap|salary|payroll)\b",
    r"\b(bao\s+hiem|bhxh|bhyt|insurance)\b",
    r"\b(thong\s+tin\s+ca\s+nhan|ho\s+so\s+nhan\s+su|personal\s+data)\b",
    r"\b(so\s+tai\s+khoan|tai\s+khoan\s+ngan\s+hang|bank\s+account)\b",
    r"\b(can\s+cuoc|cccd|cmnd|passport|ho\s+chieu)\b",
    r"\b(mat\s+khau|password|otp|ma\s+xac\s+thuc)\b",
    r"\b(dia\s+chi\s+nha|so\s+dien\s+thoai\s+ca\s+nhan)\b",
]

THIRD_PARTY_PATTERNS = [
    r"\b(cua|cho|ve)\s+(nguyen|tran|le|pham|hoang|huynh|phan|vu|vo|dang|bui|do|ho|ngo|duong)\b",
    r"\b(cua|cho|ve)\s+(anh|chi|ban|dong\s+nghiep|nhan\s+vien)\s+[a-z0-9]",
    r"\bnguoi\s+khac\b",
    r"\bdong\s+nghiep\b",
    r"\bnhan\s+vien\s+khac\b",
    r"\b[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}\b",
]

SELF_PATTERNS = [
    r"\b(cua|ve)\s+(toi|minh|em|anh|chi|ban\s+than)\b",
    r"\b(toi|minh|em)\s+(co|con|duoc|da)\b",
    r"\b(my|mine|myself)\b",
]


@dataclass(frozen=True)
class GuardrailDecision:
    allowed: bool
    refusal_reason: RefusalReason | None = None


def evaluate_chat_guardrails(message: str) -> GuardrailDecision:
    return _evaluate_rule_guardrails(message)


def looks_like_hr_question(message: str) -> bool:
    normalized = _normalize(message)
    tokens = set(_tokens(normalized))
    if tokens.intersection({term for term in HR_TERMS if " " not in term}):
        return True
    return any(term in normalized for term in HR_TERMS if " " in term)


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
    if not has_sensitive_field:
        return False

    # Credentials and identity numbers are unsafe even when the target is ambiguous.
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

    return _matches_any(normalized, THIRD_PARTY_PATTERNS)


def _is_outside_scope(normalized: str) -> bool:
    if not _matches_any(normalized, OUTSIDE_SCOPE_PATTERNS):
        return False

    # If the user is asking about an HR policy that happens to mention a broad word
    # like "du lich", keep it in scope for retrieval/escalation handling.
    return not looks_like_hr_question(normalized)


def _matches_any(text: str, patterns: list[str]) -> bool:
    return any(re.search(pattern, text) for pattern in patterns)


def _normalize(message: str) -> str:
    normalized = unicodedata.normalize("NFKD", message.lower())
    ascii_text = "".join(char for char in normalized if not unicodedata.combining(char))
    ascii_text = re.sub(r"[^a-z0-9@._%+\-\s]", " ", ascii_text)
    return re.sub(r"\s+", " ", ascii_text).strip()


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]{2,}", text)
