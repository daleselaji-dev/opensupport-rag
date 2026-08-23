"""Two-person Golden Set review protocol.

The review file is local runtime state and intentionally ignored by Git. A
release gate can only pass when two distinct reviewers have signed every case.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
BENCHMARK = ROOT / "evals" / "customer_support_benchmark_v0.3.json"
SIGNOFFS = ROOT / "data" / "golden_review_signoffs.json"


def case_ids() -> list[str]:
    payload = json.loads(BENCHMARK.read_text(encoding="utf-8"))
    return [str(item["case_id"]) for item in payload.get("cases", [])]


def read_signoffs() -> dict[str, Any]:
    if not SIGNOFFS.exists():
        return {"benchmark_version": "customer-support-v0.3-golden-draft", "reviewers": []}
    try:
        return json.loads(SIGNOFFS.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"benchmark_version": "customer-support-v0.3-golden-draft", "reviewers": [], "corrupt": True}


def review_status() -> dict[str, Any]:
    ids = set(case_ids())
    payload = read_signoffs()
    reviewers = payload.get("reviewers", [])
    normalized = []
    for reviewer in reviewers:
        approved = set(str(item) for item in reviewer.get("approved_case_ids", []))
        normalized.append({
            "role": reviewer.get("role"),
            "reviewer": reviewer.get("reviewer"),
            "approved_count": len(approved & ids),
            "missing_count": len(ids - approved),
            "notes": reviewer.get("notes", ""),
        })
    distinct = {str(item.get("reviewer")) for item in reviewers if item.get("reviewer")}
    approved = len(distinct) >= 2 and len(normalized) >= 2 and all(item["missing_count"] == 0 for item in normalized)
    return {
        "benchmark_version": "customer-support-v0.3-golden-draft",
        "case_count": len(ids),
        "reviewers": normalized,
        "distinct_reviewer_count": len(distinct),
        "approved": approved,
        "status": "approved" if approved else "draft_pending_two_person_human_review",
        "missing_reviewer_slots": max(0, 2 - len(distinct)),
    }


def record_signoff(role: str, reviewer: str, approved_case_ids: list[str], notes: str = "") -> dict[str, Any]:
    ids = set(case_ids())
    unknown = sorted(set(approved_case_ids) - ids)
    if unknown:
        raise ValueError(f"存在不属于 Golden Set 的 case_id：{', '.join(unknown[:5])}")
    reviewer = reviewer.strip()
    if len(reviewer) < 2:
        raise ValueError("reviewer 名称至少需要 2 个字符。")
    payload = read_signoffs()
    reviewers = [item for item in payload.get("reviewers", []) if item.get("role") != role]
    reviewers.append({
        "role": role,
        "reviewer": reviewer,
        "approved_case_ids": sorted(set(approved_case_ids)),
        "notes": notes[:2000],
    })
    output = {"benchmark_version": "customer-support-v0.3-golden-draft", "reviewers": reviewers}
    SIGNOFFS.parent.mkdir(parents=True, exist_ok=True)
    temp = SIGNOFFS.with_suffix(".tmp")
    temp.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temp, SIGNOFFS)
    return review_status()
