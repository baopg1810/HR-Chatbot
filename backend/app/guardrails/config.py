from __future__ import annotations

from app.config import get_settings


def guardrails_enabled() -> bool:
    settings = get_settings()
    return settings.guardrails_enabled and settings.guardrails_mode != "off"


def should_enforce_guardrails() -> bool:
    settings = get_settings()
    return guardrails_enabled() and settings.guardrails_mode == "block"


def should_warn_only() -> bool:
    settings = get_settings()
    return guardrails_enabled() and settings.guardrails_mode == "warn"
