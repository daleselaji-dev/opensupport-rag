"""Generate a human-review form from the frozen Golden Set.

The packet does not approve any case. It gives two independent reviewers the
same question, expected evidence URLs, source-type requirements and safety
boundary so their signoffs are reproducible and auditable.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BENCHMARK = ROOT / "evals" / "customer_support_benchmark_v0.3.json"
OUTPUT = ROOT / "evals" / "customer_support_benchmark_v0.3_review_form.md"


def main() -> None:
    payload = json.loads(BENCHMARK.read_text(encoding="utf-8"))
    cases = payload.get("cases", [])
    lines = [
        "# OpenSupport Golden Review Form",
        "",
        "> This is a review worksheet, not an approval. Two independent reviewers must inspect every case and submit complete case IDs through `/api/eval/golden-review/signoff`.",
        "",
        f"- Benchmark: `{payload.get('benchmark_version')}`",
        f"- Cases: `{len(cases)}`",
        "- Reviewer must check: expected source really supports the question; required source types are complete; refusal boundary is safe; bilingual labels are correct.",
        "- Do not approve a case merely because a URL is topically related.",
        "",
    ]
    for index, case in enumerate(cases, start=1):
        lines.extend([
            f"## {index:02d}. `{case['case_id']}`",
            "",
            f"- Question: {case.get('question', '')}",
            f"- Language: `{case.get('language', '')}`",
            f"- Expected action: `{case.get('expected_action', 'answer')}`",
            f"- Slices: `{', '.join(case.get('slices', []))}`",
            f"- Required source types: `{', '.join(case.get('required_source_types', [])) or 'none'}`",
            "- Expected source URLs:",
        ])
        urls = case.get("expected_source_urls", [])
        lines.extend(f"  - {url}" for url in urls) if urls else lines.append("  - none")
        forbidden = case.get("forbidden_claims", [])
        lines.extend([
            f"- Forbidden claims: `{', '.join(forbidden) or 'none'}`",
            "- Reviewer decision: `[ ] approve evidence mapping  [ ] reject / revise`",
            "- Reviewer note:",
            "",
        ])
    OUTPUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print({"status": "written", "path": str(OUTPUT), "case_count": len(cases)})


if __name__ == "__main__":
    main()
