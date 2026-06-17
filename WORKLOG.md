# Worklog - HR Helpdesk AI

## Project Objective

Build an AI-powered HR helpdesk MVP that helps employees ask HR policy questions, receive cited answers, safely look up personal HR metrics, and escalate sensitive/complex cases to HR admin.

## Work Summary

| Date | Area | Work Completed | Evidence |
|------|------|----------------|----------|
| 15/06/2026 | Product planning | Created idea, research, scope, PRD, ADR, API contract | `flow/00-idea.md` to `flow/05-contract.md` |
| 15/06/2026 | Build planning | Created build cards `C-001` to `C-010` | `cards/` |
| 15/06/2026 | Backend scaffold | Created FastAPI app, health check, docs, OpenAPI, status route | `src/main.py`, `src/api/routes.py` |
| 15/06/2026 | Auth | Added JWT demo login and `/me` endpoint | `src/services/auth.py`, `src/services/demo_users.py` |
| 15/06/2026 | RAG | Added document ingestion, chunking, lexical retrieval, citations | `src/services/documents.py`, `src/services/retrieval.py` |
| 15/06/2026 | Security | Added RBAC retrieval filters and guardrails | `src/services/guardrails.py` |
| 15/06/2026 | HR tools | Added HR metric lookup and escalation tickets | `src/services/hris.py`, `src/services/tickets.py` |
| 15/06/2026 | Trending/feedback | Added trend pins and feedback endpoint | `src/services/trending.py`, `src/services/feedback.py` |
| 15/06/2026 | Testing | Added contract/API/agent tests | `tests/test_api/`, `tests/test_agents/` |
| 15/06/2026 | Frontend | Added UI mock and React/Vite frontend app | `mockups/hr-helpdesk.html`, `fontend/` |
| 15/06/2026 | E2E | Added live demo verification and metrics report | `scripts/e2e_demo.py`, `tests/e2e/test_demo_flow.py`, `eval/results/report.md` |
| 16/06/2026 | Documentation | Added weekly module report and improved README | `weekle_report.md`, `README.md` |
| 16/06/2026 | UI polish | Converted frontend display text to Vietnamese with accents | `src/static/hr-helpdesk.html`, `src/static/slice.html` |
| 16/06/2026 | AI logs | Backfilled prompt logs for submission | `.ai-log/archive/2026-06-16.jsonl` |
| 17/06/2026 | Submission docs | Updated Journal and Worklog for final submission | `JOURNAL.md`, `WORKLOG.md` |

## Technical Decisions

| Decision | Choice | Reason | Trade-off |
|----------|--------|--------|-----------|
| Backend framework | FastAPI | Fast to build, typed validation, automatic OpenAPI docs | Requires Python runtime and ASGI server |
| API style | Contract-first REST API | Easy to test and connect frontend | Less flexible than event-driven architecture |
| Frontend | React 18 + Vite + TypeScript in `fontend/` | Supports routing, components and richer demo UX | Requires separate `npm run dev` server |
| Auth | Demo JWT with role claims | Enough for MVP RBAC and protected endpoints | Not production SSO/SCIM |
| Retrieval | RAG lexical retrieval for MVP | Deterministic, offline-friendly, testable | Less semantic than embeddings/vector DB |
| Vector path | Chroma-ready local persistence | Keeps migration path for real vector retrieval | Current MVP still relies heavily on local/simple stores |
| Guardrails | Code-level checks before answer generation | Stronger than prompt-only safety | Needs ongoing expansion of rules |
| HR metrics | Safe mock HRIS adapter | Demonstrates function calling without production HRIS risk | Mock data only |
| Escalation | Ticket object in app store | Shows human handoff workflow | Needs persistent DB and admin workflow for production |
| Trending | Query log + threshold topic detection | Demonstrates proactive HR communication | Summary still simple and rule-based |
| Testing | Unit/API/contract/e2e tests | Proves behavior and PRD metrics | E2E requires running local app |

## Module Notes

### API Scaffold

- Entry point: `src/main.py`
- Main routes: `src/api/routes.py`
- Exposes `/health`, `/docs`, `/openapi.json`, `/app`, and `/api/v1/*`.

### Authentication

- Demo users:
  - `employee@example.com` / `employee123`
  - `admin@example.com` / `admin123`
- JWT token stores role and user context.
- Employee and HR admin flows are separated by role checks.

### RAG And Citations

- HR admin can upload/register policy documents.
- Documents are chunked and indexed for retrieval.
- Policy questions return citations with document title, section, excerpt and score.
- If no source exists, the assistant refuses or escalates instead of guessing.

### RBAC And Guardrails

- Retrieval filters apply before answer generation.
- Employee cannot retrieve HR-admin-only content.
- Guardrails handle:
  - jailbreak attempts
  - out-of-scope prompts
  - sensitive requests about another person
  - no-source policy questions

### HR Metrics

- Current mock metrics include:
  - leave days remaining
  - insurance status
  - reward review status
- Endpoint never accepts arbitrary employee id from employee role.

### Escalation Tickets

- Sensitive questions create high-priority tickets.
- HR admin can list and update ticket status.
- Ticket status supports open, in_progress and resolved.

### Trending And Feedback

- Chat queries are logged by topic.
- Repeated leave questions create a trend pin.
- Feedback records whether an answer was helpful.

### Frontend

- Main frontend: `fontend/`
- Run command: `cd fontend && npm run dev`
- Local URL: `http://localhost:3000/app/`
- Backend API URL in dev: `http://localhost:8000/api/v1`
- Static fallback: `src/static/hr-helpdesk.html`
- Main capabilities:
  - login as employee/admin
  - chat with citations
  - upload documents
  - run trending
  - view/update tickets
  - submit feedback

## Bugs And Fixes

| Issue | Root Cause | Fix |
|-------|------------|-----|
| README described frontend as only static HTML | Project also has a separate React/Vite frontend in `fontend/` | Updated docs to show backend and frontend run separately |
| E2E failed when app was not running | E2E test intentionally targets live `127.0.0.1:8000` | Start uvicorn before running live e2e; documented command in README |
| Trend pin could already exist on repeated demo runs | Live in-memory server state may persist between runs | E2E treats "created or already present" trend pin as success |
| Sensitive HR data could be asked through chat | Needed explicit guardrail before retrieval/answer | Added sensitive prompt detection and escalation ticket creation |
| Employee might see admin-only policy if retrieval ignored role | Retrieval initially needed role filtering | Added RBAC filter before citation generation |

## Testing Log

| Command | Purpose | Result |
|---------|---------|--------|
| `.\.venv\Scripts\python.exe -m pytest tests/test_api/test_routes.py` | Baseline route test | Passed |
| `.\.venv\Scripts\python.exe -m pytest tests/test_api/test_static_app.py` | Static app and frontend API flow | Passed |
| `.\.venv\Scripts\python.exe -m pytest tests/e2e/test_demo_flow.py -q` | Live C-010 demo verification | Passed |
| `.\.venv\Scripts\python.exe -m pytest tests -q` | Full suite | `49 passed` |
| `cd fontend && npm run dev` | Start React frontend | Runs Vite on port 3000 |
| `cd fontend && npm run lint` | TypeScript frontend check | Passed |
| `cd fontend && npm run build` | Production frontend build | Blocked by Windows `EPERM` writing `fontend/dist`; source transform completed before file write failed |

## E2E Metrics

Source: `eval/results/report.md`

| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| Seeded policy questions | 30 | 30 | PASS |
| Cited policy answers | >= 90% | 30/30 (100.0%) | PASS |
| P95 chat latency | < 10s | 0.625s | PASS |
| Safe HR metric lookups | 5 | 5 | PASS |
| Escalation tickets | 3 | 3 | PASS |
| Trend pin after similar queries | 1 | Nghi phep | PASS |

## Current Risks

- In-memory stores are not production-ready; data resets when the process restarts.
- Demo auth is not enterprise SSO.
- RAG lexical retrieval is deterministic but less powerful than semantic vector search.
- Gemini integration is configured but the MVP keeps deterministic local behavior for tests.
- Frontend requires a separate Node/Vite process during development.

## Next Actions

1. Add SQLite/Postgres persistence for users, documents, tickets, query logs and feedback.
2. Replace RAG retrieval with Chroma/pgvector semantic retrieval.
3. Add real Gemini answer synthesis with citation-grounding guardrails.
4. Deploy the app and produce a public demo URL.
5. Prepare video demo and pitch deck.
6. Add richer HR admin analytics for feedback and repeated topics.
