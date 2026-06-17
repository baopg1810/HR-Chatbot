# Evaluation Report

## C-010 End-to-End Demo Verification

- Status: PASS
- App URL: http://127.0.0.1:8000
- Run time: 2026-06-15T04:43:10.613906+00:00
- Report path: `eval/results/report.md`

## PRD Success Metrics

| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| Seeded policy questions | 30 | 30 | PASS |
| Cited policy answers | >= 90% | 30/30 (100.0%) | PASS |
| P95 chat latency | < 10s | 0.625s | PASS |
| Safe HR metric lookups | 5 | 5 | PASS |
| Escalation tickets | 3 | 3 | PASS |
| Trend pin after similar queries | 1 | Nghi phep | PASS |

## Demo Flow Evidence

- Seeded documents: C010 Chinh sach nghi phep, C010 HR Admin Salary Controls
- RBAC leak check: no restricted citations returned; citations returned: 0
- Feedback submit: ok for `msg-d45c220f-488c-4508-9ccc-b1cbbcddfe56`
- Admin ticket update: `ticket-c6d08012-f6bf-41c6-b560-9a7e27c8e84d` -> in_progress
- Policy latency median: 0.494s
- Policy latency max: 0.715s

## Command

```powershell
.\.venv\Scripts\python.exe -m pytest tests/e2e/test_demo_flow.py -q
```
