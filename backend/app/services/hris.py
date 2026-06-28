from __future__ import annotations

from datetime import date
import re
import unicodedata

from app.models.schemas import PersonalHrMetrics, User
from app.services.retrieval import embed_text


_METRICS = {
    "emp-001": PersonalHrMetrics(
        employee_id="emp-001",
        leave_days_remaining=8.5,
        insurance_status="active",
        reward_review_status="in_review",
        as_of_date=date.today().isoformat(),
    ),
    "hr-001": PersonalHrMetrics(
        employee_id="hr-001",
        leave_days_remaining=11.0,
        insurance_status="active",
        reward_review_status="approved",
        as_of_date=date.today().isoformat(),
    ),
}

METRIC_TERMS = {
    "ngay",
    "phep",
    "con",
    "lai",
    "bao",
    "hiem",
    "trang",
    "thai",
    "khen",
    "thuong",
    "xet",
    "duyet",
    "leave",
    "insurance",
    "reward",
}

SELF_REFERENCE_TERMS = {
    "toi",
    "minh",
    "em",
    "my",
    "mine",
    "me",
    "personal",
}

METRIC_INTENT_TERMS = {
    "con",
    "lai",
    "trang",
    "thai",
    "xet",
    "duyet",
    "bao",
    "nhieu",
    "status",
    "remaining",
}


def get_personal_hr_metrics(user: User) -> PersonalHrMetrics:
    user_id = str(user.id)
    if getattr(user, "email", None) == "employee@example.com":
        user_id = "emp-001"
    elif getattr(user, "email", None) == "admin@example.com":
        user_id = "hr-001"

    metrics = _METRICS.get(user_id)
    if metrics is not None:
        return metrics
    return PersonalHrMetrics(
        employee_id=user_id,
        leave_days_remaining=0.0,
        insurance_status="pending",
        reward_review_status="not_started",
        as_of_date=date.today().isoformat(),
    )


def should_call_hris_tool(message: str) -> bool:
    """Return True only when the user asks for their own HRIS data.

    Policy questions often contain words like "ngay phep", "bao hiem", or
    "bao nhieu". Those must stay in the RAG path unless the user clearly refers
    to their own personal record.
    """
    normalized = _normalize(message)
    tokens = set(embed_text(message))
    return (
        bool(tokens.intersection(METRIC_TERMS))
        and bool(tokens.intersection(SELF_REFERENCE_TERMS))
        and bool(tokens.intersection(METRIC_INTENT_TERMS))
        and _has_self_reference(normalized)
    )


def is_hr_metric_query(message: str) -> bool:
    """Backward-compatible alias for tests/imports."""
    return should_call_hris_tool(message)


def _has_self_reference(normalized: str) -> bool:
    return any(
        re.search(pattern, normalized)
        for pattern in (
            r"\b(toi|minh|em)\b",
            r"\b(cua|ve)\s+(toi|minh|em)\b",
            r"\b(my|mine|me|personal)\b",
        )
    )


def _normalize(message: str) -> str:
    normalized = unicodedata.normalize("NFKD", message.lower().replace("đ", "d"))
    ascii_text = "".join(char for char in normalized if not unicodedata.combining(char))
    ascii_text = re.sub(r"[^a-z0-9\s]", " ", ascii_text)
    return re.sub(r"\s+", " ", ascii_text).strip()
