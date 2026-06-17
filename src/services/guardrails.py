from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from src.services.retrieval import embed_text


RefusalReason = Literal["jailbreak", "outside_scope", "sensitive", "no_source"]

HR_TERMS = {
    "hr",
    "nhan",
    "vien",
    "nghi",
    "phep",
    "luong",
    "thuong",
    "bao",
    "hiem",
    "hop",
    "dong",
    "cham",
    "cong",
    "phuc",
    "loi",
    "quy",
    "trinh",
    "chinh",
    "sach",
    "noi",
    "bo",
    "hanh",
    "chinh",
}

JAILBREAK_TERMS = {
    "ignore previous",
    "ignore all previous",
    "system prompt",
    "developer message",
    "jailbreak",
    "bo qua huong dan",
    "quen tat ca chi dan",
}

OUTSIDE_SCOPE_TERMS = {
    "weather",
    "thoi tiet",
    "bitcoin",
    "bong da",
    "football",
    "nau an",
    "recipe",
    "du lich",
}

SENSITIVE_TERMS = {
    "luong cua",
    "salary of",
    "bao hiem cua nguoi khac",
    "thong tin ca nhan cua",
    "so tai khoan",
    "can cuoc",
    "cccd",
    "mat khau",
}


@dataclass(frozen=True)
class GuardrailDecision:
    allowed: bool
    refusal_reason: RefusalReason | None = None


def evaluate_chat_guardrails(message: str) -> GuardrailDecision:
    normalized = _normalize(message)
    if any(term in normalized for term in JAILBREAK_TERMS):
        return GuardrailDecision(allowed=False, refusal_reason="jailbreak")
    if any(term in normalized for term in SENSITIVE_TERMS):
        return GuardrailDecision(allowed=False, refusal_reason="sensitive")
    if any(term in normalized for term in OUTSIDE_SCOPE_TERMS):
        return GuardrailDecision(allowed=False, refusal_reason="outside_scope")
    return GuardrailDecision(allowed=True)


def looks_like_hr_question(message: str) -> bool:
    tokens = set(embed_text(message))
    return bool(tokens.intersection(HR_TERMS))


def _normalize(message: str) -> str:
    return " ".join(embed_text(message).keys())
