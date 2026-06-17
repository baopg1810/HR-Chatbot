from pathlib import Path

from scripts.e2e_demo import DEFAULT_BASE_URL, run_demo


def test_c010_live_demo_flow_meets_prd_metrics():
    results = run_demo(base_url=DEFAULT_BASE_URL, report_path=Path("eval/results/report.md"))

    assert results["passed"] is True
    assert results["policy_questions"]["total"] == 30
    assert results["policy_questions"]["citation_rate_percent"] >= 90
    assert results["policy_questions"]["p95_seconds"] < 10
    assert results["metrics"]["successful"] == 5
    assert results["escalations"]["created"] == 3
    assert results["trending"]["created_or_present"] is True
