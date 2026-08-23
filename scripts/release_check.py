"""Objective release-readiness audit for the portfolio repository."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def main() -> None:
    quality = read_json(ROOT / "data" / "data_quality_latest.json")
    retrieval = read_json(ROOT / "reports" / "eval_latest_v0_3_hybrid.json")
    answer = read_json(ROOT / "reports" / "answer_eval_latest_v0_2.json")
    contextual = read_json(ROOT / "reports" / "eval_latest_v0_5_hybrid.json")
    stability = read_json(ROOT / "reports" / "stability_latest.json")
    golden_draft = read_json(ROOT / "evals" / "customer_support_benchmark_v0.3.json")
    review_signoffs = read_json(ROOT / "data" / "golden_review_signoffs.json")
    reviewers = review_signoffs.get("reviewers", [])
    benchmark_ids = {str(item.get("case_id")) for item in read_json(ROOT / "evals" / "customer_support_benchmark_v0.3.json").get("cases", [])}
    review_approved = len({str(item.get("reviewer")) for item in reviewers if item.get("reviewer")}) >= 2 and all(benchmark_ids.issubset(set(item.get("approved_case_ids", []))) for item in reviewers[:2])
    checks = [
        {"key": "complaints", "actual": quality.get("source_types", {}).get("complaint", 0), "target": 200, "passed": quality.get("source_types", {}).get("complaint", 0) >= 200},
        {"key": "duplicates", "actual": quality.get("duplicate_documents", "missing"), "target": 0, "passed": quality.get("duplicate_documents") == 0},
        {"key": "manifest", "actual": retrieval.get("index_inventory", {}).get("manifest_indexed_documents", "missing"), "target": retrieval.get("index_inventory", {}).get("qdrant_points", "missing"), "passed": retrieval.get("index_inventory", {}).get("manifest_indexed_documents") == retrieval.get("index_inventory", {}).get("qdrant_points")},
        {"key": "retrieval_hit_at_3", "actual": retrieval.get("metrics", {}).get("hit_at_3", 0), "target": 0.9, "passed": retrieval.get("metrics", {}).get("hit_at_3", 0) >= 0.9},
        {"key": "answer_eval", "actual": answer.get("overall_passed", False), "target": True, "passed": answer.get("overall_passed", False) is True},
        {"key": "contextual_eval", "actual": contextual.get("metrics", {}).get("hit_at_3", 0), "target": 0.9, "passed": contextual.get("metrics", {}).get("hit_at_3", 0) >= 0.9},
        {"key": "stability_error_rate", "actual": stability.get("error_rate", "missing"), "target": 0.01, "passed": isinstance(stability.get("error_rate"), (int, float)) and stability.get("error_rate", 1) <= 0.01},
        {"key": "golden_review", "actual": "approved" if review_approved else golden_draft.get("review_status", "missing"), "target": "approved", "passed": review_approved},
    ]
    result = {"release_ready": all(check["passed"] for check in checks), "checks": checks, "note": "Release readiness is blocked until every gate passes; a strong retrieval score cannot override data or answer-safety failures."}
    reports = ROOT / "reports"
    reports.mkdir(exist_ok=True)
    (reports / "release_check_latest.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result["release_ready"] else 2)


if __name__ == "__main__":
    main()
