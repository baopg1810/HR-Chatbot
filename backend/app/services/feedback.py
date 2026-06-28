from __future__ import annotations

from typing import Any

from app.models.schemas import FeedbackCreate, User
from app.database.session import get_db_context
from app.models.feedback import Feedback as DBFeedback
from app.models.chat import ChatMessage
from app.services.tickets import safe_parse_uuid

async def create_feedback(user: User, payload: FeedbackCreate, db: Any = None) -> None:
    user_uuid = safe_parse_uuid(user.id)
    msg_uuid = safe_parse_uuid(payload.message_id)

    if not user_uuid or not msg_uuid:
        raise ValueError("Invalid user_id or message_id")

    # Check if message exists in DB
    if db is not None:
        msg = await db.get(ChatMessage, msg_uuid)
        if not msg:
            raise ValueError("Unknown message id")
    else:
        async with get_db_context() as session:
            msg = await session.get(ChatMessage, msg_uuid)
            if not msg:
                raise ValueError("Unknown message id")

    db_feedback = DBFeedback(
        message_id=msg_uuid,
        user_id=user_uuid,
        rating=payload.rating,
        comment=payload.comment
    )

    if db is not None:
        db.add(db_feedback)
        await db.commit()
    else:
        async with get_db_context() as session:
            session.add(db_feedback)
            await session.commit()

def reset_feedback_store() -> None:
    pass

