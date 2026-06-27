from typing import Any, Literal

from pydantic import BaseModel, Field


Role = Literal["employee", "department_admin", "hr_admin"]


class User(BaseModel):
    id: str
    email: str
    full_name: str
    role: Role
    department_id: str | None = None


class LoginRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=320)
    password: str = Field(..., min_length=1, max_length=200)


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: Literal["bearer"] = "bearer"
    user: User


class TokenRefreshRequest(BaseModel):
    refresh_token: str = Field(..., min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: Literal["bearer"] = "bearer"


class LogoutRequest(BaseModel):
    refresh_token: str = Field(..., min_length=1)


class LogoutResponse(BaseModel):
    ok: bool = True
    message: str = "Logged out"


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=5000, description="User message")
    session_id: str | None = None


class Citation(BaseModel):
    document_id: str
    document_title: str
    section: str | None = None
    excerpt: str
    page: int | None = None
    score: float


class ChatAction(BaseModel):
    type: Literal["hr_metric_lookup", "escalation_confirmation_required", "escalation_created", "none"]
    label: str
    data: dict[str, Any] | None = None


class ChatResponse(BaseModel):
    message_id: str
    session_id: str
    answer: str
    citations: list[Citation] = Field(default_factory=list)
    actions: list[ChatAction] = Field(default_factory=list)
    escalated_ticket_id: str | None = None
    refusal_reason: str | None = None


DocumentStatus = Literal["uploaded", "indexing", "indexed", "failed"]


class DocumentCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=300)
    content: str = Field(..., min_length=1)
    visibility_roles: list[Role] = Field(default_factory=lambda: ["employee", "department_admin", "hr_admin"])
    department_ids: list[str] = Field(default_factory=list)


class Document(BaseModel):
    id: str
    title: str
    status: DocumentStatus
    visibility_roles: list[Role]
    department_ids: list[str]
    created_at: str
    chunk_count: int


class DocumentIngestResult(BaseModel):
    document: Document
    indexed_chunk_count: int
    warnings: list[str] = Field(default_factory=list)


class DocumentListResponse(BaseModel):
    documents: list[Document]


InsuranceStatus = Literal["active", "pending", "inactive"]
RewardReviewStatus = Literal["not_started", "in_review", "approved", "rejected"]
TicketStatus = Literal["open", "in_progress", "resolved"]
TicketPriority = Literal["low", "normal", "high"]
EscalationReason = Literal["no_source", "outside_scope", "sensitive", "user_requested", "low_confidence"]


class PersonalHrMetrics(BaseModel):
    employee_id: str
    leave_days_remaining: float
    insurance_status: InsuranceStatus
    reward_review_status: RewardReviewStatus
    as_of_date: str


class EscalationCreate(BaseModel):
    session_id: str | None = None
    message: str = Field(..., min_length=1, max_length=5000)
    reason: EscalationReason
    priority: TicketPriority = "normal"


class Ticket(BaseModel):
    id: str
    requester_id: str
    status: TicketStatus
    priority: TicketPriority
    reason: str
    summary: str
    assignee_id: str | None = None
    created_at: str
    updated_at: str


class TicketListResponse(BaseModel):
    tickets: list[Ticket]


class TicketUpdate(BaseModel):
    status: TicketStatus | None = None
    assignee_id: str | None = None
    internal_note: str | None = None


class TrendRunRequest(BaseModel):
    window_minutes: int = Field(default=60, ge=1, le=10080)
    threshold: int = Field(default=5, ge=1, le=1000)


class TrendCandidate(BaseModel):
    id: str
    topic_key: str
    title: str
    summary: str
    source_query_count: int
    citations: list[Citation] = Field(default_factory=list)
    created_at: str


class TrendPin(TrendCandidate):
    expires_at: str | None = None


class TrendRunResponse(BaseModel):
    created_candidates: list[TrendCandidate]
    skipped_topics: list[str] = Field(default_factory=list)


class TrendCandidatesResponse(BaseModel):
    candidates: list[TrendCandidate]


class TrendPinsResponse(BaseModel):
    pins: list[TrendPin]


FeedbackRating = Literal["up", "down"]


class FeedbackCreate(BaseModel):
    message_id: str = Field(..., min_length=1)
    rating: FeedbackRating
    comment: str | None = None


class FeedbackResponse(BaseModel):
    ok: bool = True
