from __future__ import annotations

import logging
from typing import Any

from app.config import get_settings

logger = logging.getLogger("app.guardrails")


def log_guardrail_decision(stage: str, payload: dict[str, Any]) -> None:
    settings = get_settings()
    if not settings.guardrail_log_decisions:
        return

    safe_payload = {
        "event": "guardrail_decision",
        "stage": stage,
        "allowed": payload.get("allowed"),
        "action": payload.get("action"),
        "risk_level": payload.get("risk_level"),
        "topic": payload.get("topic"),
        "confidence": payload.get("confidence"),
        "reason_code": payload.get("reason_code") or payload.get("internal_reason"),
    }
    if settings.guardrail_log_raw_text:
        safe_payload["raw_text"] = payload.get("raw_text")
    logger.info("guardrail_decision", extra={"guardrail": safe_payload})


def log_guardrail_error(stage: str, exc: Exception) -> None:
    logger.warning(
        "guardrail_error",
        extra={
            "guardrail": {
                "event": "guardrail_error",
                "stage": stage,
                "error_type": exc.__class__.__name__,
            }
        },
    )
