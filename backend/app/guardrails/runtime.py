from __future__ import annotations

from app.config import get_settings
from app.guardrails.config import guardrails_enabled, should_enforce_guardrails, should_warn_only
from app.guardrails.logging import log_guardrail_decision, log_guardrail_error
from app.guardrails.messages import GENERAL_SAFETY_MESSAGE
from app.guardrails.openai_safeguard import OpenAISafeguardClient
from app.guardrails.rules import evaluate_chat_guardrails, looks_like_hr_question  # noqa: F401
from app.guardrails.rules import (
    is_low_risk_self_service_or_helpdesk,
    rule_input_safeguard,
    rule_output_safeguard,
    rule_tool_guardrail,
    rule_topic_scope,
)
from app.guardrails.schemas import (
    InputSafeguardDecision,
    OutputSafeguardDecision,
    ToolGuardrailDecision,
    TopicScopeDecision,
)
from app.guardrails.topic_classifier import GemmaTopicClassifier


async def check_input_safeguard(text: str, user_context: dict | None = None) -> InputSafeguardDecision:
    settings = get_settings()
    if not guardrails_enabled():
        return InputSafeguardDecision(
            allowed=True,
            action="allow",
            risk_level="none",
            user_message="",
            internal_reason="guardrails_disabled",
            reason_code="allow",
        )
    if not settings.openai_safeguard_enabled:
        return _warn_to_allow(rule_input_safeguard(text))

    rule_decision = rule_input_safeguard(text)
    if not _safeguard_provider_configured(settings) or _running_under_pytest():
        log_guardrail_decision("input", rule_decision.model_dump())
        return _warn_to_allow(rule_decision)

    try:
        provider_decision = await OpenAISafeguardClient().check_input(text, user_context=user_context)
    except Exception as exc:
        log_guardrail_error("input", exc)
        decision = rule_decision if not rule_decision.allowed else _decision_for_guardrail_error("input_safeguard_error")
    else:
        decision = _combine_input_safeguards(rule_decision, provider_decision)
    log_guardrail_decision("input", decision.model_dump())
    return _warn_to_allow(decision)


async def check_topic_scope(text: str) -> TopicScopeDecision:
    settings = get_settings()
    if not guardrails_enabled() or not settings.topic_classifier_enabled:
        return TopicScopeDecision(
            scope="in_scope",
            topic="disabled",
            sensitivity="normal",
            confidence=1.0,
            user_message="",
            internal_reason="guardrails_disabled",
        )

    rule_decision = rule_topic_scope(text)
    if (
        settings.topic_classifier_provider != "gemma"
        or not (settings.google_api_key or settings.google_api_keys)
        or _running_under_pytest()
    ):
        log_guardrail_decision("topic", rule_decision.model_dump())
        return rule_decision

    try:
        decision = await GemmaTopicClassifier().classify(text)
    except Exception as exc:
        log_guardrail_error("topic", exc)
        if is_low_risk_self_service_or_helpdesk(text):
            decision = rule_decision
        elif settings.guardrails_fail_closed and should_enforce_guardrails():
            decision = TopicScopeDecision(
                scope="ambiguous",
                topic="guardrail_error",
                sensitivity="normal",
                confidence=0.0,
                user_message=GENERAL_SAFETY_MESSAGE,
                internal_reason="topic_classifier_error_fail_closed",
            )
        else:
            decision = rule_decision
    log_guardrail_decision("topic", decision.model_dump())
    return decision


async def check_output_safeguard(
    text: str,
    *,
    user_message: str = "",
    context_summary: str = "",
    has_citations: bool = False,
    has_tool_result: bool = False,
    topic: str = "",
) -> OutputSafeguardDecision:
    settings = get_settings()
    if not guardrails_enabled() or not settings.output_guardrail_enabled:
        return OutputSafeguardDecision(
            allowed=True,
            action="allow",
            risk_level="none",
            user_message="",
            redacted_text=None,
            internal_reason="guardrails_disabled",
        )

    rule_decision = rule_output_safeguard(
        text,
        user_message=user_message,
        context_summary=context_summary,
        has_citations=has_citations,
        has_tool_result=has_tool_result,
        topic=topic,
    )
    if (
        not settings.openai_safeguard_enabled
        or not _safeguard_provider_configured(settings)
        or _running_under_pytest()
    ):
        log_guardrail_decision("output", rule_decision.model_dump())
        return _warn_output_to_allow(rule_decision, text)

    try:
        provider_decision = await OpenAISafeguardClient().check_output(
            text,
            context={
                "user_message": user_message,
                "context_summary": context_summary,
                "has_tool_result": has_tool_result,
                "topic": topic,
            },
        )
    except Exception as exc:
        log_guardrail_error("output", exc)
        if not rule_decision.allowed:
            decision = rule_decision
        elif settings.guardrails_fail_closed and should_enforce_guardrails():
            decision = OutputSafeguardDecision(
                allowed=False,
                action="fallback",
                risk_level="medium",
                user_message=GENERAL_SAFETY_MESSAGE,
                redacted_text=None,
                internal_reason="output_safeguard_error_fail_closed",
            )
        else:
            decision = rule_decision
    else:
        decision = _combine_output_safeguards(rule_decision, provider_decision)
    if rule_decision.allowed and not decision.allowed and (has_tool_result or topic == "hr_helpdesk_usage"):
        decision = rule_decision.model_copy(update={"internal_reason": "provider_false_positive_low_risk"})
    log_guardrail_decision("output", decision.model_dump())
    return _warn_output_to_allow(decision, text)


async def check_tool_guardrail(
    tool_name: str,
    user: object | None,
    *,
    side_effect: bool = False,
) -> ToolGuardrailDecision:
    settings = get_settings()
    if not guardrails_enabled() or not settings.tool_guardrail_enabled:
        return ToolGuardrailDecision(
            allowed=True,
            action="allow",
            tool_name=tool_name,
            risk_level="low",
            user_message="",
            internal_reason="guardrails_disabled",
        )
    decision = rule_tool_guardrail(tool_name, user, side_effect=side_effect)
    log_guardrail_decision("tool", decision.model_dump())
    if should_warn_only():
        return decision.model_copy(update={"allowed": True, "action": "allow"})
    return decision


def _warn_to_allow(decision: InputSafeguardDecision) -> InputSafeguardDecision:
    if should_warn_only():
        return decision.model_copy(update={"allowed": True, "blocked": False, "action": "allow"})
    return decision


def _warn_output_to_allow(decision: OutputSafeguardDecision, original_text: str) -> OutputSafeguardDecision:
    if should_warn_only():
        return OutputSafeguardDecision(
            allowed=True,
            action="allow",
            risk_level=decision.risk_level,
            user_message="",
            redacted_text=original_text,
            internal_reason=f"warn_only:{decision.internal_reason}",
        )
    return decision


def _combine_input_safeguards(
    rule_decision: InputSafeguardDecision,
    provider_decision: InputSafeguardDecision,
) -> InputSafeguardDecision:
    if not rule_decision.allowed or rule_decision.blocked:
        return rule_decision
    return provider_decision


def _combine_output_safeguards(
    rule_decision: OutputSafeguardDecision,
    provider_decision: OutputSafeguardDecision,
) -> OutputSafeguardDecision:
    if not rule_decision.allowed:
        return rule_decision
    return provider_decision


def _decision_for_guardrail_error(reason: str) -> InputSafeguardDecision:
    settings = get_settings()
    if settings.guardrails_fail_closed and should_enforce_guardrails():
        return InputSafeguardDecision(
            allowed=False,
            blocked=True,
            action="fallback",
            risk_level="medium",
            user_message=GENERAL_SAFETY_MESSAGE,
            internal_reason=f"{reason}_fail_closed",
            reason_code="guardrail_error",
        )
    return InputSafeguardDecision(
        allowed=True,
        action="allow",
        risk_level="low",
        user_message="",
        internal_reason=f"{reason}_fail_open",
        reason_code="guardrail_error",
    )


def _running_under_pytest() -> bool:
    import os

    return "PYTEST_CURRENT_TEST" in os.environ


def _safeguard_provider_configured(settings) -> bool:
    if settings.safeguard_provider == "groq":
        return bool(settings.groq_api_key or settings.groq_api_keys)
    return bool(settings.openai_api_key)
