from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from src.models.schemas import FeedbackCreate, User
from src.services.trending import message_exists


@dataclass
class FeedbackRecord:
    message_id: str
    user_id: str
    rating: str
    comment: str | None
    created_at: str


_FEEDBACK: list[FeedbackRecord] = []


def create_feedback(user: User, payload: FeedbackCreate) -> None:
    if not message_exists(payload.message_id):
        raise ValueError("Unknown message id")
    _FEEDBACK.append(
        FeedbackRecord(
            message_id=payload.message_id,
            user_id=user.id,
            rating=payload.rating,
            comment=payload.comment,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
    )


def reset_feedback_store() -> None:
    _FEEDBACK.clear()
