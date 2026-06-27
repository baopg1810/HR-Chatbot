from __future__ import annotations

from datetime import date

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

PERSONAL_TERMS = {
    "toi",
    "minh",
    "cua",
    "ban",
    "con",
    "lai",
    "my",
    "mine",
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



def is_hr_metric_query(message: str) -> bool:
    tokens = set(embed_text(message))
    return (
        bool(tokens.intersection(METRIC_TERMS))
        and bool(tokens.intersection(PERSONAL_TERMS))
        and bool(tokens.intersection(METRIC_INTENT_TERMS))
    )
