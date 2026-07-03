from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, Field


RefusalReason = Literal["jailbreak", "outside_scope", "sensitive", "no_source"]
RiskLevel = Literal["none", "low", "medium", "high"]


@dataclass(frozen=True)
class GuardrailDecision:
    allowed: bool
    refusal_reason: RefusalReason | None = None


class GuardrailError(Exception):
    pass


class GuardrailProviderError(GuardrailError):
    pass


class GuardrailParseError(GuardrailError):
    pass


class InputSafeguardDecision(BaseModel):
    allowed: bool
    blocked: bool = False
    requires_handoff: bool = False
    action: Literal["allow", "block", "handoff", "fallback"] = "allow"
    risk_level: RiskLevel = "none"
    user_message: str = ""
    internal_reason: str = ""
    reason_code: str = "allow"


class TopicScopeDecision(BaseModel):
    scope: Literal["in_scope", "out_of_scope", "ambiguous"]
    topic: str
    sensitivity: Literal["normal", "sensitive", "confidential"]
    confidence: float = Field(ge=0.0, le=1.0)
    user_message: str
    internal_reason: str


class OutputSafeguardDecision(BaseModel):
    allowed: bool
    action: Literal["allow", "redact", "block", "fallback"]
    risk_level: RiskLevel
    user_message: str
    redacted_text: str | None = None
    internal_reason: str


class ToolGuardrailDecision(BaseModel):
    allowed: bool
    action: Literal["allow", "require_auth", "require_confirmation", "block", "handoff"]
    tool_name: str
    risk_level: Literal["low", "medium", "high"]
    user_message: str
    internal_reason: str
