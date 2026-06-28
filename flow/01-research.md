# Stage 01 - Research (inspect first)

Rule: INSPECT what already exists. Evidence required - links, quotes, screenshots.
"I think there's nothing like this" without searching = gate fail.

Research date: 2026-06-13.

## Gate - check ALL before `/flow next`
- [x] I actually OPENED 3 existing tools/competitors (links below, with one honest note each)
- [x] I found 3 REAL user complaints online and quoted them (with source links)
- [x] I wrote what competitors CHARGE (real prices) and who is paying them
- [x] I named the ONE channel my first 10 users come from (a place, not "social media")
- [x] I wrote why those users would pick this over the status quo (one honest paragraph)
- [x] I wrote what is technically free vs hard for this idea
- [x] No FILL placeholders remain in this file

## What exists already (3 - open them, don't guess)

1. ServiceNow HR Service Delivery - https://www.servicenow.com/products/hr-service-delivery.html - Very strong enterprise HR workflow suite. It already promises AI front door, agentic self-service, case management, and escalation, but it is heavy enterprise software and likely too expensive/slow for a course MVP or mid-size local deployment.
2. Freshservice for IT and Employee Service - https://www.freshworks.com/freshservice/pricing/ - Strong service desk with employee-service channels, workflows, knowledge base, Teams/Slack support, and transparent pricing. It is broader than HR and does not give a lightweight local-first RAG assistant with Vietnamese policy citations out of the box.
3. Atlassian Service Collection / Jira Service Management - https://www.atlassian.com/collections/service/pricing - Strong request intake, HR templates, knowledge base, Rovo AI, virtual service agent, and enterprise controls. It works best for teams already in Atlassian and can feel like a service-management platform rather than a simple HR answer assistant.

## What users say (3 real complaints, quoted, with source)

1. > "We will look into it." - Employee story about HR ignoring repeated issues for 6 months: https://m.economictimes.com/magazines/panache/hr-ignored-his-3-issues-for-6-months-with-we-will-look-into-it-when-asked-the-reason-his-resignation-answer-stunned-hr/articleshow/131028994.cms
2. > "personal reasons" - Employee leave/privacy story where HR still demanded details: https://m.economictimes.com/magazines/panache/employee-says-leave-is-for-personal-reasons-hr-still-demands-to-know-the-reason-netizens-say-say-you-may-/articleshow/125540527.cms
3. > "Received a call from HR" - Onboarding miscommunication story where a new hire learned she was not actually hired: https://m.economictimes.com/magazines/panache/woman-on-first-day-of-new-job-realises-she-was-never-even-hired-by-the-company-received-a-call-from-hr-/articleshow/131631404.cms

## GTM & business reality

Building is the cheap part now. Distribution and willingness-to-pay are where ideas die -
research them BEFORE planning, not after shipping.

### Who pays today, and how much (pricing reference points)

- Freshservice - official pricing lists Starter $19/agent/month, Growth $49/agent/month, Pro $99/agent/month billed annually, and Enterprise as tailored quote/custom. Buyers are IT/employee-service teams paying per support agent: https://www.freshworks.com/freshservice/pricing/
- Atlassian Service Collection - official pricing lists Free for 3 agents, Standard $20/agent/month, Premium $51.42/agent/month, and Enterprise via sales. Buyers are service-management teams; customers/requesters are unlimited and unlicensed: https://www.atlassian.com/collections/service/pricing
- ServiceNow HRSD - official HRSD page sells AI agents and HR case/workflow automation, but pricing is sales-led/custom. Buyers are enterprise HR/IT transformation teams, usually with procurement and implementation budget: https://www.servicenow.com/products/hr-service-delivery.html

### The first-10-users channel (one, named)

AI20K/Cohort 2 builders and their workplaces: ask classmates/team members who have HR/admin policy documents in Vietnamese and can simulate or test repeated internal policy questions. This channel is reachable now through the course community and gives realistic seed data without enterprise procurement.

### Why switch (vs the status quo)

The first users would pick this over chat groups, email, or manual HR replies because it gives immediate answers with visible citations and a clear handoff path when the AI should not decide. The local wedge is not "a bigger ServiceNow"; it is a fast, Vietnamese-first HR policy assistant that can be demoed with a company's own policy PDFs and a small HR metrics adapter.

## Technically free vs hard

- Free (solved by libraries/platforms): FastAPI API docs, JWT libraries, LangGraph routing, Gemini API calls, embedding generation, vector search with Chroma or pgvector, CRUD ticket endpoints, basic dashboards, threshold-based trending summaries.
- Hard (custom work, real risk): high-quality document chunking/citations for legal HR text, role-based retrieval filtering, hallucination guardrails, safe HRIS function calling, privacy controls for personal data, model/version drift, and turning "many similar questions" into useful trending topics without noisy clustering.
