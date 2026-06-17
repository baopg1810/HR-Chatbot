# Stage 03 - PRD

1-2 pages max. Test: could a stranger build v1 from this without asking you anything?

## Gate - check ALL before `/flow next`
- [x] Every section below is filled from MY scope decision (stage 02), not re-expanded
- [x] Success metric is a NUMBER, not vibes ("save time" fails; "first response < 2h" passes)
- [x] Each feature names the user action and the observable result
- [x] Pain & gain is a MAPPING TABLE: every pain cites evidence (a stage-01 quote or a named observation), and names the v1 feature that kills it; every v1 feature kills at least one pain
- [x] A stranger could build v1 from this without asking me anything
- [x] No FILL placeholders remain in this file

## Context

HR Helpdesk AI enters an organization where HR policy answers are scattered across documents, chat history, and individual HR staff knowledge. Employees want quick answers for leave, salary/benefit rules, insurance, and internal procedures, but HR teams lose time answering repeated questions and clarifying new policy changes. The v1 product is a web app with employee chat, citation-backed RAG, safe personal metric lookup, escalation to HR, and a small HR admin dashboard for trends and tickets.

## Target users

- Employee: internal employee/can bo/giang vien who needs answers about policies, leave, insurance, and personal HR status.
- HR admin: HR staff member who owns policy documents, monitors repeated questions, and resolves escalated tickets.
- Department admin: authorized administrative staff who may see department-scoped policy answers but not sensitive personal data outside their role.

## Pain & gain (mapping table - the traceability spine of the PRD)

| # | Persona | Pain (concrete) | Evidence (stage-01 quote/source or named observation) | Today's workaround | V1 feature that kills it | Observable gain |
|---|---|---|---|---|---|---|
| P1 | Employee | Waits for HR on simple policy questions | Quote: "We will look into it." Source: Economic Times HR ignored issues story | Email/chat HR and wait | Policy Q&A with citations | Employee gets answer with source in under 10 seconds |
| P2 | HR admin | Repeats answers to the same leave/pay/insurance questions | Named observation from project brief: HR repeatedly answers basic questions | Copy/paste old replies, answer in group chat | Policy Q&A, trending summary, pinned notices | Repeated topic becomes a pinned notice after threshold |
| P3 | Employee | Needs personal HR figures without exposing extra private detail | Quote: "personal reasons" Source: Economic Times leave/privacy story | Ask HR directly or share private context | Personal HR metrics lookup with RBAC | Employee sees own leave/insurance/reward status only |
| P4 | HR admin | Complex or sensitive cases need a human, not an AI answer | Named observation from project brief: issues may exceed AI authority | Manual handoff through email/chat | Escalation tickets | Ticket is created with status and conversation summary |
| P5 | HR admin | Policy documents are hard to keep searchable and current | Competitor evidence: enterprise tools sell knowledge/case management | Manually search PDFs and old announcements | Admin document upload and re-index | New policy document appears in search results with citations |
| P6 | HR admin | Cannot tell whether answers are trusted | MVP quality-control need from stage 02 | Ask users informally | Answer feedback | Admin can view useful/not useful counts per answer |

### Pains NOT addressed in v1 (deliberate - tie to the scope cut list)

- Production HRIS write actions - deferred because approving leave, changing payroll, or changing insurance status requires real workflow authorization.
- Enterprise SSO and SCIM - deferred because JWT role login is sufficient for local MVP.
- Slack/Teams bot - deferred because web chat proves the workflow before channel expansion.

## Problem statement

Internal HR teams spend too much time answering repeated administrative questions while employees wait for simple policy and personal-status answers. HR Helpdesk AI should answer within seconds, cite official sources, protect data by role, and escalate safely when AI should not resolve the case.

## Features (user-centric - action -> observable result)

- As an employee, I ask an HR policy question, and I see an answer with citations containing document title, section, and excerpt.
- As an employee, I ask for my leave balance, insurance status, or reward-review status, and I see only my own HR metrics returned by a safe function call.
- As an employee, I ask something outside policy scope or too sensitive for AI, and I see a ticket created for HR with a ticket id.
- As an HR admin, I upload or register a policy document, and the document becomes available for cited search after indexing.
- As an HR admin, I view trending topics, and I see pinned summaries generated only after query volume crosses a threshold.
- As an HR admin, I view escalated tickets, and I can update ticket status from open to in_progress to resolved.
- As any user, I mark an answer helpful or not helpful, and HR can see feedback counts.

## Non-functional requirements

- Answers must include at least one citation for policy questions or clearly refuse if no relevant source is found.
- Role filters must be applied before generation, not only after answer text is produced.
- Personal HR metric endpoints must require token auth and must never accept arbitrary employee_id from employee role.
- P95 chat response target for demo data: under 10 seconds.
- Store model name, retrieval ids, citations, role, and escalation reason for audit/debug.
- Use Vietnamese-ready UTF-8 data, while code/config stays simple and testable.

## Tech stack

- Backend: Python FastAPI, Pydantic, LangGraph.
- AI: Gemini API, stable Gemini 3.1 Flash-Lite where available, Gemini Embedding 2 for embeddings; pin exact model strings in config and avoid deprecated preview model ids.
- Data: SQLite for MVP app records, Chroma local vector store for MVP retrieval; planned migration path to Postgres + pgvector.
- Auth/security: JWT, role claims, retrieval filters, prompt guardrails, refusal categories.
- Frontend: simple web chat plus HR admin dashboard, built after API contract.
- Deploy target: Dockerized FastAPI app locally first; later Render/Fly.io/Railway style host.

## Success metric (numbers only)

- 30 seeded HR policy questions answered in demo with >= 90% having at least one correct citation.
- P95 response time under 10 seconds on demo dataset.
- 5 personal HR metric lookups return correct mock HRIS values with no cross-user leakage.
- 3 out-of-scope/sensitive questions create escalation tickets.
- 1 trending topic gets pinned after at least 5 similar queries.
