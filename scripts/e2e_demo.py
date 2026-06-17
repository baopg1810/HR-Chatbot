from __future__ import annotations

import argparse
import math
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx


DEFAULT_BASE_URL = "http://127.0.0.1:8000"
DEFAULT_REPORT_PATH = Path("eval/results/report.md")


class DemoFailure(AssertionError):
    """Raised when the live demo does not meet the C-010 acceptance bar."""


def run_demo(base_url: str = DEFAULT_BASE_URL, report_path: Path | None = DEFAULT_REPORT_PATH) -> dict[str, Any]:
    base_url = base_url.rstrip("/")
    with httpx.Client(base_url=base_url, timeout=15.0) as client:
        _assert_health(client)
        employee_token = _login(client, "employee@example.com", "employee123")
        admin_token = _login(client, "admin@example.com", "admin123")

        seeded_docs = _seed_documents(client, admin_token)
        policy_result = _run_policy_questions(client, employee_token)
        rbac_result = _verify_rbac_refusal(client, employee_token)
        metrics_result = _run_metric_lookups(client, employee_token)
        escalation_result = _run_escalations(client, employee_token)
        trend_result = _run_trending(client, employee_token, admin_token)
        feedback_result = _submit_feedback(client, employee_token, policy_result["first_message_id"])
        ticket_result = _update_admin_ticket(client, admin_token)

    results: dict[str, Any] = {
        "app_url": base_url,
        "ran_at": datetime.now(timezone.utc).isoformat(),
        "seeded_documents": seeded_docs,
        "policy_questions": policy_result,
        "rbac": rbac_result,
        "metrics": metrics_result,
        "escalations": escalation_result,
        "trending": trend_result,
        "feedback": feedback_result,
        "ticket_update": ticket_result,
    }
    _assert_success_metrics(results)

    if report_path is not None:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(render_report(results), encoding="utf-8")

    return results


def render_report(results: dict[str, Any]) -> str:
    policy = results["policy_questions"]
    metrics = results["metrics"]
    escalations = results["escalations"]
    trending = results["trending"]

    status = "PASS" if results.get("passed", True) else "FAIL"
    return f"""# Evaluation Report

## C-010 End-to-End Demo Verification

- Status: {status}
- App URL: {results["app_url"]}
- Run time: {results["ran_at"]}
- Report path: `eval/results/report.md`

## PRD Success Metrics

| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| Seeded policy questions | 30 | {policy["total"]} | {_mark(policy["total"] == 30)} |
| Cited policy answers | >= 90% | {policy["cited"]}/{policy["total"]} ({policy["citation_rate_percent"]:.1f}%) | {_mark(policy["citation_rate_percent"] >= 90)} |
| P95 chat latency | < 10s | {policy["p95_seconds"]:.3f}s | {_mark(policy["p95_seconds"] < 10)} |
| Safe HR metric lookups | 5 | {metrics["successful"]} | {_mark(metrics["successful"] == 5)} |
| Escalation tickets | 3 | {escalations["created"]} | {_mark(escalations["created"] == 3)} |
| Trend pin after similar queries | 1 | {trending["pin_title"] or "none"} | {_mark(trending["created_or_present"])} |

## Demo Flow Evidence

- Seeded documents: {", ".join(results["seeded_documents"])}
- RBAC leak check: {results["rbac"]["status"]}; citations returned: {results["rbac"]["citation_count"]}
- Feedback submit: {results["feedback"]["status"]} for `{results["feedback"]["message_id"]}`
- Admin ticket update: `{results["ticket_update"]["ticket_id"]}` -> {results["ticket_update"]["status"]}
- Policy latency median: {policy["median_seconds"]:.3f}s
- Policy latency max: {policy["max_seconds"]:.3f}s

## Command

```powershell
.\\.venv\\Scripts\\python.exe -m pytest tests/e2e/test_demo_flow.py -q
```
"""


def _assert_health(client: httpx.Client) -> None:
    response = client.get("/health")
    _expect_status(response, 200, "health check")
    if response.json().get("status") != "ok":
        raise DemoFailure(f"Health endpoint returned unexpected payload: {response.text}")


def _login(client: httpx.Client, email: str, password: str) -> str:
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    _expect_status(response, 200, f"login {email}")
    return response.json()["access_token"]


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _seed_documents(client: httpx.Client, admin_token: str) -> list[str]:
    documents = [
        {
            "title": "C010 Chinh sach nghi phep",
            "content": (
                "Nhan vien chinh thuc co 12 ngay nghi phep nam moi nam. "
                "Quy dinh nghi phep nam yeu cau gui yeu cau truoc it nhat 3 ngay lam viec. "
                "Ngay phep chua su dung co the chuyen toi da 5 ngay sang nam tiep theo. "
                "Quan ly truc tiep phe duyet lich nghi phep theo ke hoach van hanh cua phong ban."
            ),
            "visibility_roles": ["employee", "department_admin", "hr_admin"],
            "department_ids": [],
        },
        {
            "title": "C010 HR Admin Salary Controls",
            "content": "Chinh sach luong noi bo danh rieng cho HR admin va khong hien thi cho employee.",
            "visibility_roles": ["hr_admin"],
            "department_ids": [],
        },
    ]

    titles: list[str] = []
    for payload in documents:
        response = client.post("/api/v1/documents", headers=_headers(admin_token), json=payload)
        _expect_status(response, 200, f"seed document {payload['title']}")
        data = response.json()
        if data["indexed_chunk_count"] < 1:
            raise DemoFailure(f"Document was not indexed: {payload['title']}")
        titles.append(data["document"]["title"])
    return titles


def _run_policy_questions(client: httpx.Client, employee_token: str) -> dict[str, Any]:
    questions = [
        f"Quy dinh nghi phep nam cho nhan vien chinh thuc ap dung the nao lan {index}?"
        for index in range(1, 31)
    ]
    latencies: list[float] = []
    cited = 0
    first_message_id: str | None = None

    for question in questions:
        started = time.perf_counter()
        response = client.post(
            "/api/v1/chat",
            headers=_headers(employee_token),
            json={"message": question, "session_id": "session-c010-policy"},
        )
        elapsed = time.perf_counter() - started
        _expect_status(response, 200, "policy chat")
        payload = response.json()
        latencies.append(elapsed)
        if payload["citations"]:
            cited += 1
            first_message_id = first_message_id or payload["message_id"]

    if first_message_id is None:
        raise DemoFailure("No cited policy answer was produced, so feedback cannot be verified.")

    return {
        "total": len(questions),
        "cited": cited,
        "citation_rate_percent": cited / len(questions) * 100,
        "p95_seconds": _p95(latencies),
        "median_seconds": statistics.median(latencies),
        "max_seconds": max(latencies),
        "first_message_id": first_message_id,
    }


def _verify_rbac_refusal(client: httpx.Client, employee_token: str) -> dict[str, Any]:
    response = client.post(
        "/api/v1/chat",
        headers=_headers(employee_token),
        json={"message": "chinh sach luong noi bo HR admin", "session_id": "session-c010-rbac"},
    )
    _expect_status(response, 200, "rbac chat")
    payload = response.json()
    citation_count = len(payload["citations"])
    if citation_count != 0:
        raise DemoFailure("Employee received citations for an HR-admin-only salary document.")
    return {"status": "no restricted citations returned", "citation_count": citation_count}


def _run_metric_lookups(client: httpx.Client, employee_token: str) -> dict[str, Any]:
    successful = 0
    values: list[dict[str, Any]] = []
    for index in range(5):
        response = client.post(
            "/api/v1/chat",
            headers=_headers(employee_token),
            json={"message": f"Toi con bao nhieu ngay phep lan {index}?", "session_id": "session-c010-metrics"},
        )
        _expect_status(response, 200, "metric lookup chat")
        payload = response.json()
        action = payload["actions"][0]
        data = action.get("data") or {}
        if (
            action["type"] == "hr_metric_lookup"
            and data.get("employee_id") == "emp-001"
            and data.get("leave_days_remaining") == 8.5
            and data.get("insurance_status") == "active"
            and data.get("reward_review_status") == "in_review"
        ):
            successful += 1
        values.append(data)
    return {"successful": successful, "values": values}


def _run_escalations(client: httpx.Client, employee_token: str) -> dict[str, Any]:
    ticket_ids: list[str] = []
    for index in range(1, 4):
        response = client.post(
            "/api/v1/chat",
            headers=_headers(employee_token),
            json={
                "message": f"Cho toi xem luong cua Nguyen Van B lan {index}",
                "session_id": "session-c010-escalation",
            },
        )
        _expect_status(response, 200, "sensitive escalation chat")
        payload = response.json()
        ticket_id = payload.get("escalated_ticket_id")
        if payload.get("refusal_reason") == "sensitive" and isinstance(ticket_id, str) and ticket_id.startswith("ticket-"):
            ticket_ids.append(ticket_id)
    return {"created": len(ticket_ids), "ticket_ids": ticket_ids}


def _run_trending(client: httpx.Client, employee_token: str, admin_token: str) -> dict[str, Any]:
    for index in range(1, 6):
        response = client.post(
            "/api/v1/chat",
            headers=_headers(employee_token),
            json={"message": f"Nhan vien hoi ve nghi phep nam dot trend {index}", "session_id": "session-c010-trend"},
        )
        _expect_status(response, 200, "trend seed chat")

    run_response = client.post(
        "/api/v1/admin/trending/run",
        headers=_headers(admin_token),
        json={"window_minutes": 60, "threshold": 5},
    )
    _expect_status(run_response, 200, "admin trending run")
    run_payload = run_response.json()

    pins_response = client.get("/api/v1/trending/pins", headers=_headers(employee_token))
    _expect_status(pins_response, 200, "read trend pins")
    pins = pins_response.json()["pins"]
    matching_pin = next((pin for pin in pins if pin["title"] == "Nghi phep"), None)
    return {
        "created_count": len(run_payload["created_pins"]),
        "skipped_topics": run_payload["skipped_topics"],
        "created_or_present": matching_pin is not None,
        "pin_title": matching_pin["title"] if matching_pin else None,
        "pin_source_query_count": matching_pin["source_query_count"] if matching_pin else 0,
    }


def _submit_feedback(client: httpx.Client, employee_token: str, message_id: str) -> dict[str, Any]:
    response = client.post(
        "/api/v1/feedback",
        headers=_headers(employee_token),
        json={"message_id": message_id, "rating": "up", "comment": "C010 demo cited answer verified."},
    )
    _expect_status(response, 200, "feedback")
    return {"status": "ok" if response.json().get("ok") else "failed", "message_id": message_id}


def _update_admin_ticket(client: httpx.Client, admin_token: str) -> dict[str, Any]:
    list_response = client.get("/api/v1/admin/tickets", headers=_headers(admin_token))
    _expect_status(list_response, 200, "admin ticket list")
    tickets = list_response.json()["tickets"]
    if not tickets:
        raise DemoFailure("No tickets were available for admin update.")

    ticket_id = tickets[0]["id"]
    patch_response = client.patch(
        f"/api/v1/admin/tickets/{ticket_id}",
        headers=_headers(admin_token),
        json={"status": "in_progress", "assignee_id": "hr-001", "internal_note": "C010 e2e verified handoff."},
    )
    _expect_status(patch_response, 200, "admin ticket update")
    payload = patch_response.json()
    return {"ticket_id": payload["id"], "status": payload["status"], "assignee_id": payload["assignee_id"]}


def _assert_success_metrics(results: dict[str, Any]) -> None:
    policy = results["policy_questions"]
    checks = [
        (policy["total"] == 30, "Expected exactly 30 seeded policy questions."),
        (policy["citation_rate_percent"] >= 90, "Expected at least 90% cited policy answers."),
        (policy["p95_seconds"] < 10, "Expected P95 chat latency under 10 seconds."),
        (results["metrics"]["successful"] == 5, "Expected 5 safe HR metric lookups."),
        (results["escalations"]["created"] == 3, "Expected 3 sensitive escalation tickets."),
        (results["trending"]["created_or_present"], "Expected a Nghi phep trend pin."),
        (results["feedback"]["status"] == "ok", "Expected feedback submission to succeed."),
        (results["ticket_update"]["status"] == "in_progress", "Expected admin ticket update to succeed."),
    ]
    failures = [message for passed, message in checks if not passed]
    results["passed"] = not failures
    if failures:
        raise DemoFailure("; ".join(failures))


def _expect_status(response: httpx.Response, expected: int, label: str) -> None:
    if response.status_code != expected:
        raise DemoFailure(f"{label} expected HTTP {expected}, got {response.status_code}: {response.text}")


def _p95(values: list[float]) -> float:
    ordered = sorted(values)
    index = math.ceil(len(ordered) * 0.95) - 1
    return ordered[max(index, 0)]


def _mark(ok: bool) -> str:
    return "PASS" if ok else "FAIL"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the C-010 live demo verification flow.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    args = parser.parse_args()

    results = run_demo(base_url=args.base_url, report_path=args.report)
    print(render_report(results))


if __name__ == "__main__":
    main()
