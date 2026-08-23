"""Create a reviewer packet for the 50-case Golden Draft."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    path = ROOT / "evals" / "customer_support_benchmark_v0.3.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    cases = payload.get("cases", [])
    ids = [case.get("case_id") for case in cases]
    duplicate_ids = sorted(case_id for case_id, count in Counter(ids).items() if count > 1)
    missing_urls = [case["case_id"] for case in cases if case.get("expected_action") == "answer" and not case.get("expected_source_urls")]
    unsafe_answerable = [case["case_id"] for case in cases if case.get("expected_action") == "answer" and not case.get("required_source_types")]
    refusal_without_forbidden = [case["case_id"] for case in cases if case.get("expected_action") == "refuse_or_escalate" and not case.get("forbidden_claims")]
    slices = Counter(slice_name for case in cases for slice_name in case.get("slices", []))
    result = {
        "benchmark_version": payload.get("benchmark_version"),
        "review_status": payload.get("review_status"),
        "case_count": len(cases),
        "answerable_cases": sum(case.get("expected_action") == "answer" for case in cases),
        "refusal_cases": sum(case.get("expected_action") == "refuse_or_escalate" for case in cases),
        "duplicate_case_ids": duplicate_ids,
        "answerable_missing_urls": missing_urls,
        "answerable_missing_required_source_types": unsafe_answerable,
        "refusal_missing_forbidden_claims": refusal_without_forbidden,
        "slice_counts": dict(slices),
        "reviewer_questions": [
            "每个 expected_source_urls 是否真的支持问题，而不是仅仅相关？",
            "required_source_types 是否完整，是否遗漏 regulation 或 guidance？",
            "refuse_or_escalate 是否真的不能由公开证据回答？",
            "forbidden_claims 是否覆盖该问题的主要风险？",
            "中文问题的中问英检标签是否准确？",
        ],
        "approved": False,
    }
    out = ROOT / "reports" / "benchmark_review_v0_3.json"
    out.parent.mkdir(exist_ok=True)
    serialized = json.dumps(result, ensure_ascii=False, indent=2)
    out.write_text(serialized, encoding="utf-8")
    # Keep a small review artifact in the tracked eval package so a fresh
    # checkout can see the last audit contract even though runtime reports are
    # intentionally ignored.
    (ROOT / "evals" / "customer_support_benchmark_v0.3_review_packet.json").write_text(
        serialized + "\n", encoding="utf-8"
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
