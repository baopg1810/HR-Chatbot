# Stage 02 - Scope (go/no-go)

Scope = features chosen by IMPACT x COST, inside your time budget.
KILL here is cheap and smart. Killing a weak idea at this gate is a SUCCESS outcome.

## Impact rubric (business value - score BEFORE looking at cost)

| Impact | Meaning |
|---|---|
| H | moves money or the core promise: gets users in (acquisition), gets them paying (revenue), or delivers the one job they came for |
| M | keeps users / saves real time weekly (retention, operations) |
| L | nice-to-have; nobody would pay for or switch over it |

## AI coding grade rubric

| Grade | Meaning | Examples |
|---|---|---|
| A | cheap for AI | CRUD, forms, dashboards, content sites, API wrappers |
| B | moderate | file processing, 3rd-party integrations, auth via library, single LLM call, HITL AI drafts |
| C | expensive | realtime, payments from scratch, custom auth, autonomous agentic AI pipelines, heavy concurrency |

## Gate - check ALL before `/flow next`
- [x] Every feature below has an IMPACT (H/M/L with the business reason) AND a grade (A/B/C)
- [x] No L-impact feature above grade A survives in v1
- [x] The suggested-features section was actually considered (each suggestion has an in/out decision)
- [x] fit(grades, budget) holds - every C in scope is justified as path 1, 2, or 3 above (written next to the feature)
- [x] If the product IS a C feature: it is FIRST in build order, and its sibling C features are on the cut list
- [x] The cut list is written (what I am NOT building in v1)
- [x] GO / KILL decision is written below
- [x] No FILL placeholders remain in this file

## Time budget

30-40 focused hours for a demo MVP, using the existing FastAPI/LangGraph starter and local/mock data instead of a full enterprise integration.

## Features in v1 (each with impact AND grade)

- Policy Q&A with citations - impact H (core job: employees get trustworthy answers immediately) - grade B - use Gemini, Gemini Embedding 2, and a small vector store; keep ingestion to HR policy files and store citation metadata.
- RBAC and guardrails - impact H (security is required for HR trust) - grade B - JWT roles plus retrieval filters and refusal rules; no enterprise SSO in v1.
- Personal HR metrics lookup - impact H (high-value employee task beyond generic FAQ) - grade B - implement safe function calling against a mock HRIS adapter for leave balance, insurance status, and reward-review status.
- Escalation tickets - impact H (prevents unsafe AI decisions and gives HR a queue) - grade A - create ticket records with reason, conversation summary, priority, and status.
- Trending summary and pinned notices - impact M (reduces repeated surges when a policy changes) - grade B - re-architect realtime clustering down to thresholded query logs and batch summarization; no continuous realtime pipeline in v1.
- HR admin dashboard - impact M (helps HR see trends, tickets, and pinned answers) - grade A - simple tables/cards consuming existing endpoints.

## Suggested features (impact-first - proposed, not decided)

- Admin document upload and re-index - impact H (gets users to value using their own policies) - grade B - IN for v1, limited to PDF/text upload and manual re-index.
- Answer feedback thumbs-up/down - impact M (improves trust and gives HR signals) - grade A - IN for v1 because it is cheap and helps demo quality control.
- Slack/Teams bot integration - impact M (meets employees where they ask) - grade B - OUT for v1 because web chat proves the core and keeps auth/data simpler.

## Cut list (NOT in v1 - deferred, not deleted)

- Full HRIS production integration - deferred because real systems need credentials, data mapping, audit review, and security approval.
- Enterprise SSO/SCIM and complex org hierarchy - deferred because JWT role login is enough for the MVP contract.
- Autonomous execution of HR procedures - deferred because leave approvals, insurance changes, and payroll actions are high-risk.
- Realtime stream clustering for trending - deferred in favor of thresholded batch summary.
- Multi-tenant SaaS billing and tenant isolation - deferred because first users are internal demos, not paying external tenants.
- Voice chat and mobile app - deferred because web chat is enough to prove value.

## Decision

GO - v1 proves the core business value with cited HR answers, safe personal lookup, and human escalation while keeping enterprise-grade integrations out of scope.
