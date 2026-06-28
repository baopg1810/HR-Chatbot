from __future__ import annotations

import argparse
import html
import json
import math
import re
import statistics
import time
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx


DEFAULT_BASE_URL = "http://127.0.0.1:8000"
DEFAULT_DATASET_PATH = Path("eval/golden_dataset.json")
DEFAULT_HTML_REPORT_PATH = Path("eval/results/benchmark_report.html")
DEFAULT_JSON_REPORT_PATH = Path("eval/results/benchmark_results.json")


class BenchmarkFailure(RuntimeError):
    """Raised when the live benchmark cannot be executed."""


def run_benchmark(
    *,
    base_url: str = DEFAULT_BASE_URL,
    dataset_path: Path = DEFAULT_DATASET_PATH,
    html_report_path: Path = DEFAULT_HTML_REPORT_PATH,
    json_report_path: Path = DEFAULT_JSON_REPORT_PATH,
    seed_documents: bool = True,
    delay_seconds: float = 0.25,
    timeout_seconds: float = 60.0,
    employee_email: str = "employee@example.com",
    employee_password: str = "employee123",
    admin_email: str = "admin@example.com",
    admin_password: str = "admin123",
) -> dict[str, Any]:
    dataset = _load_dataset(dataset_path)
    base_url = base_url.rstrip("/")

    with httpx.Client(base_url=base_url, timeout=timeout_seconds) as client:
        _assert_health(client)
        employee_token = _login(client, employee_email, employee_password)
        seeded_titles: list[str] = []
        seed_error: str | None = None

        if seed_documents:
            admin_token = _login(client, admin_email, admin_password)
            try:
                seeded_titles = _seed_documents(client, admin_token, dataset.get("knowledge_base", []))
            except Exception as exc:
                seed_error = str(exc)
                raise BenchmarkFailure(
                    "Could not seed golden knowledge documents. "
                    "Run with --skip-seed if the server already has the dataset documents. "
                    f"Original error: {exc}"
                ) from exc

        case_results: list[dict[str, Any]] = []
        for index, case in enumerate(dataset["cases"], start=1):
            if index > 1 and delay_seconds > 0:
                time.sleep(delay_seconds)
            case_results.append(_run_case(client, employee_token, case, index=index))

    summary = _summarize(dataset, case_results)
    results = {
        "dataset": {
            "name": dataset.get("name"),
            "version": dataset.get("version"),
            "path": str(dataset_path),
            "case_count": len(dataset["cases"]),
        },
        "app_url": base_url,
        "ran_at": datetime.now(timezone.utc).isoformat(),
        "seeded_documents": seeded_titles,
        "seed_error": seed_error,
        "summary": summary,
        "cases": case_results,
    }

    json_report_path.parent.mkdir(parents=True, exist_ok=True)
    json_report_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    html_report_path.parent.mkdir(parents=True, exist_ok=True)
    html_report_path.write_text(render_html_report(results), encoding="utf-8")
    return results


def _load_dataset(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    cases = data.get("cases")
    if not isinstance(cases, list) or len(cases) != 20:
        raise BenchmarkFailure(f"Expected exactly 20 golden cases in {path}, found {len(cases or [])}.")
    return data


def _assert_health(client: httpx.Client) -> None:
    response = client.get("/health")
    _expect_status(response, 200, "health check")
    if response.json().get("status") not in {"ok", "ready"}:
        raise BenchmarkFailure(f"Unexpected health payload: {response.text}")


def _login(client: httpx.Client, email: str, password: str) -> str:
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    _expect_status(response, 200, f"login {email}")
    return response.json()["access_token"]


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _seed_documents(client: httpx.Client, admin_token: str, documents: list[dict[str, Any]]) -> list[str]:
    seeded: list[str] = []
    for document in documents:
        response = client.post("/api/v1/documents", headers=_headers(admin_token), json=document)
        _expect_status(response, 200, f"seed document {document.get('title')}")
        payload = response.json()
        if payload.get("indexed_chunk_count", 0) < 1:
            raise BenchmarkFailure(f"Document was accepted but not indexed: {document.get('title')}")
        seeded.append(payload["document"]["title"])
    return seeded


def _run_case(client: httpx.Client, token: str, case: dict[str, Any], *, index: int) -> dict[str, Any]:
    session_id = f"session-golden-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{index:02d}"
    measured = _chat_stream_with_retry(
        client,
        token,
        {"message": case["query"], "session_id": session_id},
    )
    evaluation = _evaluate_case(case, measured["payload"])

    return {
        "id": case["id"],
        "category": case.get("category", ""),
        "query": case["query"],
        "expected_answer": case["answer"],
        "actual_answer": measured["payload"].get("answer", ""),
        "status_code": measured["status_code"],
        "ttft_ms": measured["ttft_ms"],
        "latency_ms": measured["latency_ms"],
        "retry_after_seconds": measured["retry_after_seconds"],
        "citations": measured["payload"].get("citations", []),
        "actions": measured["payload"].get("actions", []),
        "refusal_reason": measured["payload"].get("refusal_reason"),
        "scores": evaluation["scores"],
        "checks": evaluation["checks"],
        "passed": evaluation["passed"],
    }


def _chat_stream_with_retry(
    client: httpx.Client,
    token: str,
    payload: dict[str, Any],
    *,
    max_retries: int = 2,
) -> dict[str, Any]:
    retry_after_total = 0
    for attempt in range(max_retries + 1):
        measured = _chat_stream(client, token, payload)
        if measured["status_code"] != 429:
            measured["retry_after_seconds"] = retry_after_total
            return measured

        retry_after = int(measured.get("headers", {}).get("retry-after") or 60)
        retry_after_total += retry_after
        if attempt == max_retries:
            measured["retry_after_seconds"] = retry_after_total
            return measured
        time.sleep(retry_after)

    raise AssertionError("unreachable")


def _chat_stream(client: httpx.Client, token: str, payload: dict[str, Any]) -> dict[str, Any]:
    started = time.perf_counter()
    ttft_ms: float | None = None
    events: list[tuple[str, dict[str, Any]]] = []
    status_code = 0
    headers: dict[str, str] = {}

    with client.stream("POST", "/api/v1/chat/stream", headers=_headers(token), json=payload) as response:
        status_code = response.status_code
        headers = dict(response.headers)
        if status_code == 429:
            body = response.read().decode("utf-8", errors="replace")
            elapsed_ms = (time.perf_counter() - started) * 1000
            return {
                "status_code": status_code,
                "headers": headers,
                "payload": {"answer": body, "citations": [], "actions": []},
                "ttft_ms": None,
                "latency_ms": elapsed_ms,
            }
        _expect_status(response, 200, "stream chat")

        current_event = "message"
        data_lines: list[str] = []
        for line in response.iter_lines():
            if line.startswith("event:"):
                current_event = line.split(":", 1)[1].strip()
                continue
            if line.startswith("data:"):
                data_lines.append(line.split(":", 1)[1].strip())
                continue
            if line == "":
                if data_lines:
                    data_text = "\n".join(data_lines)
                    data = json.loads(data_text)
                    if current_event == "token" and ttft_ms is None and data.get("text"):
                        ttft_ms = (time.perf_counter() - started) * 1000
                    events.append((current_event, data))
                current_event = "message"
                data_lines = []

    elapsed_ms = (time.perf_counter() - started) * 1000
    done_payload = next((data for event, data in reversed(events) if event == "done"), None)
    if done_payload is None:
        token_text = "".join(str(data.get("text", "")) for event, data in events if event == "token")
        done_payload = {"answer": token_text, "citations": [], "actions": []}
    return {
        "status_code": status_code,
        "headers": headers,
        "payload": done_payload,
        "ttft_ms": ttft_ms,
        "latency_ms": elapsed_ms,
    }


def _evaluate_case(case: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    answer = str(payload.get("answer", ""))
    citations = payload.get("citations") or []
    actions = payload.get("actions") or []
    normalized_answer = _normalize(answer)

    required_hits = _phrase_hits(normalized_answer, case.get("required_phrases", []))
    forbidden_hits = _phrase_hits(normalized_answer, case.get("forbidden_phrases", []))
    action_type = actions[0].get("type") if actions and isinstance(actions[0], dict) else None
    expected_action = case.get("expected_action_type")
    refusal_reason = payload.get("refusal_reason")

    expected_titles = case.get("expected_source_titles", [])
    citation_titles = [str(item.get("document_title", "")) for item in citations if isinstance(item, dict)]
    expected_citation_found = all(
        any(_normalize(expected) in _normalize(actual) for actual in citation_titles)
        for expected in expected_titles
    )
    citation_expectation_ok = bool(citations) if case.get("expect_citations") else not citations
    if expected_titles:
        citation_expectation_ok = citation_expectation_ok and expected_citation_found

    action_ok = expected_action is None or action_type == expected_action
    action_data_ok = _expected_action_data_ok(actions, case.get("expected_action_data", {}))
    refusal_ok = case.get("expected_refusal_reason") is None or refusal_reason == case.get("expected_refusal_reason")
    forbidden_ok = not forbidden_hits
    required_score = len(required_hits) / max(len(case.get("required_phrases", [])), 1)
    answer_similarity = _token_f1(case.get("answer", ""), answer)

    correctness = _bounded_average([required_score, 1.0 if action_ok else 0.0, 1.0 if action_data_ok else 0.0, 1.0 if refusal_ok else 0.0, 1.0 if forbidden_ok else 0.0])
    groundedness = 1.0 if citation_expectation_ok else 0.0
    relevance = _bounded_average([answer_similarity, required_score])
    overall = _bounded_average([groundedness, relevance, correctness])

    checks = {
        "required_phrases": {
            "passed": required_score >= 0.75,
            "hits": required_hits,
            "expected": case.get("required_phrases", []),
        },
        "forbidden_phrases": {
            "passed": forbidden_ok,
            "hits": forbidden_hits,
        },
        "citations": {
            "passed": citation_expectation_ok,
            "expected_source_titles": expected_titles,
            "actual_source_titles": citation_titles,
        },
        "action_type": {
            "passed": action_ok,
            "expected": expected_action,
            "actual": action_type,
        },
        "action_data": {
            "passed": action_data_ok,
            "expected": case.get("expected_action_data", {}),
        },
        "refusal_reason": {
            "passed": refusal_ok,
            "expected": case.get("expected_refusal_reason"),
            "actual": refusal_reason,
        },
    }

    return {
        "scores": {
            "groundedness": round(groundedness, 3),
            "relevance": round(relevance, 3),
            "correctness": round(correctness, 3),
            "answer_similarity": round(answer_similarity, 3),
            "overall": round(overall, 3),
        },
        "checks": checks,
        "passed": all(item["passed"] for item in checks.values()) and overall >= 0.75,
    }


def _expected_action_data_ok(actions: list[dict[str, Any]], expected: dict[str, Any]) -> bool:
    if not expected:
        return True
    action_data = {}
    for action in actions:
        if isinstance(action, dict) and isinstance(action.get("data"), dict):
            action_data.update(action["data"])
    for key, expected_value in expected.items():
        actual_value = action_data.get(key)
        if isinstance(expected_value, float):
            try:
                if not math.isclose(float(actual_value), expected_value, rel_tol=0.0, abs_tol=0.001):
                    return False
            except (TypeError, ValueError):
                return False
        elif actual_value != expected_value:
            return False
    return True


def _summarize(dataset: dict[str, Any], case_results: list[dict[str, Any]]) -> dict[str, Any]:
    latencies = [case["latency_ms"] for case in case_results if case.get("latency_ms") is not None]
    ttfts = [case["ttft_ms"] for case in case_results if case.get("ttft_ms") is not None]
    passed = sum(1 for case in case_results if case["passed"])
    cited_expected = [case for case in dataset["cases"] if case.get("expect_citations")]
    cited_actual = sum(1 for case in case_results if case["citations"])

    score_names = ["groundedness", "relevance", "correctness", "answer_similarity", "overall"]
    score_summary = {
        name: round(statistics.mean(case["scores"][name] for case in case_results), 3)
        for name in score_names
    }

    return {
        "total": len(case_results),
        "passed": passed,
        "failed": len(case_results) - passed,
        "pass_rate_percent": round(passed / max(len(case_results), 1) * 100, 1),
        "citation_rate_percent": round(cited_actual / max(len(cited_expected), 1) * 100, 1),
        "expected_cited_cases": len(cited_expected),
        "actual_cited_cases": cited_actual,
        "latency_ms": _latency_summary(latencies),
        "ttft_ms": _latency_summary(ttfts),
        "scores": score_summary,
    }


def _latency_summary(values: list[float]) -> dict[str, float | None]:
    if not values:
        return {"p50": None, "p95": None, "max": None, "mean": None}
    return {
        "p50": round(statistics.median(values), 2),
        "p95": round(_p95(values), 2),
        "max": round(max(values), 2),
        "mean": round(statistics.mean(values), 2),
    }


def _p95(values: list[float]) -> float:
    ordered = sorted(values)
    index = math.ceil(len(ordered) * 0.95) - 1
    return ordered[max(index, 0)]


def _bounded_average(values: list[float]) -> float:
    if not values:
        return 0.0
    return max(0.0, min(1.0, statistics.mean(values)))


def _phrase_hits(normalized_text: str, phrases: list[str]) -> list[str]:
    hits = []
    for phrase in phrases:
        if _normalize(phrase) in normalized_text:
            hits.append(phrase)
    return hits


def _token_f1(expected: str, actual: str) -> float:
    expected_tokens = _tokens(expected)
    actual_tokens = _tokens(actual)
    if not expected_tokens or not actual_tokens:
        return 0.0
    expected_counts = _counts(expected_tokens)
    actual_counts = _counts(actual_tokens)
    overlap = sum(min(expected_counts.get(token, 0), actual_counts.get(token, 0)) for token in expected_counts)
    if overlap == 0:
        return 0.0
    precision = overlap / len(actual_tokens)
    recall = overlap / len(expected_tokens)
    return 2 * precision * recall / (precision + recall)


def _counts(tokens: list[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for token in tokens:
        counts[token] = counts.get(token, 0) + 1
    return counts


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]{2,}", _normalize(text))


def _normalize(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", str(text).lower().replace("đ", "d"))
    ascii_text = "".join(char for char in normalized if not unicodedata.combining(char))
    ascii_text = re.sub(r"[^a-z0-9\s.]", " ", ascii_text)
    return re.sub(r"\s+", " ", ascii_text).strip()


def render_html_report(results: dict[str, Any]) -> str:
    summary = results["summary"]
    latency = summary["latency_ms"]
    ttft = summary["ttft_ms"]
    status_class = "pass" if summary["failed"] == 0 else "fail"
    status_text = "PASS" if summary["failed"] == 0 else "FAIL"

    rows = "\n".join(_render_case_row(case) for case in results["cases"])
    return f"""<!doctype html>
<html lang="vi">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Golden Benchmark Report</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f7f8fa;
      --panel: #ffffff;
      --ink: #17202a;
      --muted: #667085;
      --line: #d9dee7;
      --good: #137a3a;
      --bad: #b42318;
      --warn: #a15c00;
      --accent: #2454a6;
    }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font-family: Arial, Helvetica, sans-serif;
      line-height: 1.45;
    }}
    main {{
      max-width: 1180px;
      margin: 0 auto;
      padding: 32px 20px 48px;
    }}
    h1, h2 {{
      margin: 0 0 12px;
      letter-spacing: 0;
    }}
    .meta, .muted {{
      color: var(--muted);
      font-size: 14px;
    }}
    .summary {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 12px;
      margin: 22px 0;
    }}
    .tile {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 14px;
    }}
    .tile strong {{
      display: block;
      font-size: 24px;
      margin-top: 4px;
    }}
    .pass {{ color: var(--good); }}
    .fail {{ color: var(--bad); }}
    .warn {{ color: var(--warn); }}
    table {{
      width: 100%;
      border-collapse: collapse;
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      overflow: hidden;
    }}
    th, td {{
      border-bottom: 1px solid var(--line);
      padding: 10px;
      text-align: left;
      vertical-align: top;
      font-size: 14px;
    }}
    th {{
      background: #eef2f7;
      font-size: 13px;
      color: #344054;
    }}
    tr:last-child td {{ border-bottom: 0; }}
    details summary {{
      cursor: pointer;
      color: var(--accent);
      font-weight: 600;
    }}
    .answer {{
      max-width: 360px;
      white-space: normal;
    }}
    code {{
      background: #eef2f7;
      padding: 2px 5px;
      border-radius: 4px;
    }}
  </style>
</head>
<body>
<main>
  <h1>Golden Benchmark Report <span class="{status_class}">{status_text}</span></h1>
  <div class="meta">
    Dataset: {html.escape(str(results["dataset"]["name"]))} v{html.escape(str(results["dataset"]["version"]))}
    · App: {html.escape(results["app_url"])}
    · Run: {html.escape(results["ran_at"])}
  </div>

  <section class="summary" aria-label="summary">
    <div class="tile"><span class="muted">Pass rate</span><strong class="{status_class}">{summary["pass_rate_percent"]}%</strong></div>
    <div class="tile"><span class="muted">Cases</span><strong>{summary["passed"]}/{summary["total"]}</strong></div>
    <div class="tile"><span class="muted">Groundedness</span><strong>{summary["scores"]["groundedness"]:.3f}</strong></div>
    <div class="tile"><span class="muted">Relevance</span><strong>{summary["scores"]["relevance"]:.3f}</strong></div>
    <div class="tile"><span class="muted">Correctness</span><strong>{summary["scores"]["correctness"]:.3f}</strong></div>
    <div class="tile"><span class="muted">Answer similarity</span><strong>{summary["scores"]["answer_similarity"]:.3f}</strong></div>
    <div class="tile"><span class="muted">P95 latency</span><strong>{_fmt_ms(latency["p95"])}</strong></div>
    <div class="tile"><span class="muted">P95 TTFT</span><strong>{_fmt_ms(ttft["p95"])}</strong></div>
  </section>

  <section class="tile">
    <h2>Latency</h2>
    <p class="muted">
      Total latency ms: p50 {_fmt_ms(latency["p50"])}, p95 {_fmt_ms(latency["p95"])}, mean {_fmt_ms(latency["mean"])}, max {_fmt_ms(latency["max"])}.
      TTFT ms: p50 {_fmt_ms(ttft["p50"])}, p95 {_fmt_ms(ttft["p95"])}, mean {_fmt_ms(ttft["mean"])}, max {_fmt_ms(ttft["max"])}.
    </p>
    <p class="muted">
      Citation rate on citation-expected cases: {summary["actual_cited_cases"]}/{summary["expected_cited_cases"]} ({summary["citation_rate_percent"]}%).
    </p>
  </section>

  <h2 style="margin-top: 24px;">Case Results</h2>
  <table>
    <thead>
      <tr>
        <th>ID</th>
        <th>Status</th>
        <th>Category</th>
        <th>Query</th>
        <th>Actual Answer</th>
        <th>Scores</th>
        <th>Latency</th>
        <th>Checks</th>
      </tr>
    </thead>
    <tbody>
      {rows}
    </tbody>
  </table>
</main>
</body>
</html>
"""


def _render_case_row(case: dict[str, Any]) -> str:
    status = "PASS" if case["passed"] else "FAIL"
    status_class = "pass" if case["passed"] else "fail"
    scores = case["scores"]
    checks = html.escape(json.dumps(case["checks"], ensure_ascii=False, indent=2))
    citations = ", ".join(item.get("document_title", "") for item in case.get("citations", []) if isinstance(item, dict))
    if not citations:
        citations = "none"
    return f"""
      <tr>
        <td><code>{html.escape(case["id"])}</code></td>
        <td class="{status_class}">{status}</td>
        <td>{html.escape(case["category"])}</td>
        <td>{html.escape(case["query"])}</td>
        <td class="answer">{html.escape(case["actual_answer"])}<br><span class="muted">Citations: {html.escape(citations)}</span></td>
        <td>
          G {scores["groundedness"]:.3f}<br>
          R {scores["relevance"]:.3f}<br>
          C {scores["correctness"]:.3f}<br>
          Overall {scores["overall"]:.3f}
        </td>
        <td>
          TTFT {_fmt_ms(case["ttft_ms"])}<br>
          Total {_fmt_ms(case["latency_ms"])}
        </td>
        <td><details><summary>View</summary><pre>{checks}</pre></details></td>
      </tr>
"""


def _fmt_ms(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:.0f} ms"


def _expect_status(response: httpx.Response, expected: int, label: str) -> None:
    if response.status_code != expected:
        raise BenchmarkFailure(f"{label} expected HTTP {expected}, got {response.status_code}: {response.text}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run live chatbot benchmark against the golden dataset.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET_PATH)
    parser.add_argument("--html-report", type=Path, default=DEFAULT_HTML_REPORT_PATH)
    parser.add_argument("--json-report", type=Path, default=DEFAULT_JSON_REPORT_PATH)
    parser.add_argument("--skip-seed", action="store_true", help="Do not upload knowledge_base documents before the run.")
    parser.add_argument("--delay-seconds", type=float, default=0.25, help="Delay between cases; 429 Retry-After is still honored.")
    parser.add_argument("--timeout-seconds", type=float, default=60.0)
    parser.add_argument("--employee-email", default="employee@example.com")
    parser.add_argument("--employee-password", default="employee123")
    parser.add_argument("--admin-email", default="admin@example.com")
    parser.add_argument("--admin-password", default="admin123")
    args = parser.parse_args()

    results = run_benchmark(
        base_url=args.base_url,
        dataset_path=args.dataset,
        html_report_path=args.html_report,
        json_report_path=args.json_report,
        seed_documents=not args.skip_seed,
        delay_seconds=args.delay_seconds,
        timeout_seconds=args.timeout_seconds,
        employee_email=args.employee_email,
        employee_password=args.employee_password,
        admin_email=args.admin_email,
        admin_password=args.admin_password,
    )
    summary = results["summary"]
    print(
        f"Benchmark complete: {summary['passed']}/{summary['total']} passed, "
        f"P95 TTFT {_fmt_ms(summary['ttft_ms']['p95'])}, "
        f"P95 latency {_fmt_ms(summary['latency_ms']['p95'])}."
    )
    print(f"HTML report: {args.html_report}")
    print(f"JSON report: {args.json_report}")


if __name__ == "__main__":
    main()
