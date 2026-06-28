# Stage 04 - ADR (architecture decisions)

Short. The most valuable section is what you are NOT doing and why.

## Gate - check ALL before `/flow next`
- [x] Each decision has a one-line "why" and a one-line "what I rejected"
- [x] The NOT-doing list is written
- [x] Decisions cover: data storage, auth approach, deploy target
- [x] No FILL placeholders remain in this file

## Decisions

| # | Decision | Why | Rejected alternative |
|---|---|---|---|
| 1 | FastAPI + LangGraph backend | The repo already uses FastAPI/LangGraph, and the agent flow needs routing between retrieval, guardrails, function calling, and escalation | Node.js rewrite, because it slows the MVP and discards existing code |
| 2 | SQLite for app records in v1, Chroma for vectors | Cheap local MVP storage for users, tickets, feedback, query logs, and document chunks | Full Postgres + pgvector now, because setup/deploy cost is higher for the first slice |
| 3 | JWT auth with role claims: employee, department_admin, hr_admin | Good enough to test RBAC and retrieval filters without enterprise identity work | SSO/SCIM/custom auth, because it is security-critical integration work outside v1 |
| 4 | Gemini API with stable model ids in config | User requested Gemini, and official docs list Gemini 3.1 Flash-Lite and Gemini Embedding 2 for low-cost generation and RAG embeddings | Hard-coded preview model ids, because Google docs show preview/deprecated models can be shut down |
| 5 | RAG pipeline requires citation metadata before answer generation | Legal/policy answer trust depends on visible source title, section, and excerpt | Freeform LLM answer from uploaded text, because it cannot prove source grounding |
| 6 | Function calling only reads from a mock HRIS adapter in v1 | Proves personal lookup safely without touching real HR data | Direct connection to production HRIS, because credentials, audit, and data mapping are not available |
| 7 | Thresholded batch trending summary | Reduces the expensive realtime/C feature to a B-grade MVP while preserving user value | Realtime semantic stream clustering, because it adds concurrency and noise risk |
| 8 | Dockerized local app first | Existing Dockerfile/docker-compose make a repeatable demo path | Cloud production deployment now, because planning contract and API slice should land first |

## NOT doing in v1 (and why it's safe to skip)

- No production HRIS writes: safe because the MVP only reads mock personal metrics and escalates complex cases.
- No enterprise SSO: safe because JWT roles still prove RBAC behavior in demo.
- No multi-tenant SaaS: safe because first users are internal/course testers, not separate customer tenants.
- No realtime trend stream: safe because query-log thresholding proves the product behavior.
- No autonomous HR procedure execution: safe because human HR remains the final authority for sensitive actions.
- No Slack/Teams bot: safe because the web app proves core answer and escalation flows first.
