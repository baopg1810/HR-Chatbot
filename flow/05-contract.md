# Stage 05 - Interface Contract (the seam)

The contract is whatever sits between your core and its consumer. For this web app, that
is the HTTP API. Written BEFORE code. Backend cards build TO this table; UI cards consume
FROM it.

## Gate - check ALL before `/flow next`
- [x] Every PRD feature maps to at least one endpoint below
- [x] Every endpoint has request AND response shapes written
- [x] Auth column filled for every endpoint (public / token / admin)
- [x] No FILL placeholders remain in this file

## OpenAPI / Swagger rule

FastAPI serves `/docs` and `/openapi.json`. This table is the planning source of truth;
the served spec is the runtime artifact of the same contract.

## Endpoints

| Method | Path | Auth | Request shape | Response shape |
|---|---|---|---|---|
| GET | `/health` | public | none | `{status: "ok", env: string}` |
| POST | `/api/v1/auth/login` | public | `{email: string, password: string}` | `{access_token: string, token_type: "bearer", user: User}` |
| GET | `/api/v1/me` | token | none | `User` |
| POST | `/api/v1/chat` | token | `ChatRequest` | `ChatResponse` |
| POST | `/api/v1/documents` | admin | multipart `{file, title: string, visibility_roles: string[], department_ids?: string[]}` | `DocumentIngestResult` |
| GET | `/api/v1/documents` | admin | query `{status?: indexed|failed|pending}` | `{documents: Document[]}` |
| GET | `/api/v1/me/hr-metrics` | token | none | `PersonalHrMetrics` |
| POST | `/api/v1/escalations` | token | `EscalationCreate` | `Ticket` |
| GET | `/api/v1/admin/tickets` | admin | query `{status?: open|in_progress|resolved, priority?: low|normal|high}` | `{tickets: Ticket[]}` |
| PATCH | `/api/v1/admin/tickets/{ticket_id}` | admin | `{status?: open|in_progress|resolved, assignee_id?: string, internal_note?: string}` | `Ticket` |
| GET | `/api/v1/trending/pins` | token | none | `{pins: TrendPin[]}` |
| POST | `/api/v1/admin/trending/run` | admin | `{window_minutes: int = 60, threshold: int = 5}` | `{created_pins: TrendPin[], skipped_topics: string[]}` |
| POST | `/api/v1/feedback` | token | `{message_id: string, rating: "up"|"down", comment?: string}` | `{ok: true}` |

## Shared shapes (objects used by multiple endpoints)

```text
User {
  id: string,
  email: string,
  full_name: string,
  role: "employee"|"department_admin"|"hr_admin",
  department_id: string|null
}

ChatRequest {
  message: string,
  session_id: string|null
}

ChatResponse {
  message_id: string,
  session_id: string,
  answer: string,
  citations: Citation[],
  actions: ChatAction[],
  escalated_ticket_id: string|null,
  refusal_reason: string|null
}

Citation {
  document_id: string,
  document_title: string,
  section: string|null,
  excerpt: string,
  page: int|null,
  score: float
}

ChatAction {
  type: "hr_metric_lookup"|"escalation_created"|"none",
  label: string,
  data: object|null
}

Document {
  id: string,
  title: string,
  status: "pending"|"indexed"|"failed",
  visibility_roles: string[],
  department_ids: string[],
  created_at: string,
  chunk_count: int
}

DocumentIngestResult {
  document: Document,
  indexed_chunk_count: int,
  warnings: string[]
}

PersonalHrMetrics {
  employee_id: string,
  leave_days_remaining: float,
  insurance_status: "active"|"pending"|"inactive",
  reward_review_status: "not_started"|"in_review"|"approved"|"rejected",
  as_of_date: string
}

EscalationCreate {
  session_id: string|null,
  message: string,
  reason: "no_source"|"outside_scope"|"sensitive"|"user_requested"|"low_confidence",
  priority: "low"|"normal"|"high"
}

Ticket {
  id: string,
  requester_id: string,
  status: "open"|"in_progress"|"resolved",
  priority: "low"|"normal"|"high",
  reason: string,
  summary: string,
  assignee_id: string|null,
  created_at: string,
  updated_at: string
}

TrendPin {
  id: string,
  title: string,
  summary: string,
  source_query_count: int,
  citations: Citation[],
  created_at: string,
  expires_at: string|null
}
```

## Feature -> endpoint map

- Policy Q&A with citations -> `POST /api/v1/chat`
- RBAC and guardrails -> all token/admin endpoints, especially `POST /api/v1/chat` and `POST /api/v1/documents`
- Personal HR metrics lookup -> `GET /api/v1/me/hr-metrics`, surfaced through `POST /api/v1/chat`
- Escalation tickets -> `POST /api/v1/escalations`, `GET /api/v1/admin/tickets`, `PATCH /api/v1/admin/tickets/{ticket_id}`
- Trending summary and pinned notices -> `GET /api/v1/trending/pins`, `POST /api/v1/admin/trending/run`
- Admin document upload/re-index -> `POST /api/v1/documents`, `GET /api/v1/documents`
- Answer feedback -> `POST /api/v1/feedback`
