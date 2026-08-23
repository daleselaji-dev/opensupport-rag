"""Submit a Golden Review signoff after a human has independently reviewed all cases."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--role", required=True, choices=["reviewer_a", "reviewer_b"])
    parser.add_argument("--reviewer", required=True)
    parser.add_argument("--all-cases", action="store_true", help="仅在该 reviewer 确实逐条审阅全部 50 case 后使用")
    parser.add_argument("--case-ids-file", type=Path, help="包含已独立审阅 case_id 的文本文件，每行一个")
    parser.add_argument("--notes", default="")
    parser.add_argument("--base-url", default="http://localhost:18000")
    args = parser.parse_args()
    if args.all_cases == bool(args.case_ids_file):
        raise SystemExit("必须明确选择 --all-cases 或 --case-ids-file 其中一个")
    benchmark = json.loads((ROOT / "evals" / "customer_support_benchmark_v0.3.json").read_text(encoding="utf-8"))
    expected = [str(item["case_id"]) for item in benchmark.get("cases", [])]
    if args.all_cases:
        approved_case_ids = expected
    else:
        approved_case_ids = [line.strip() for line in args.case_ids_file.read_text(encoding="utf-8").splitlines() if line.strip()]
    payload = json.dumps({"role": args.role, "reviewer": args.reviewer, "approved_case_ids": approved_case_ids, "notes": args.notes}, ensure_ascii=False).encode("utf-8")
    request = Request(f"{args.base_url.rstrip('/')}/api/eval/golden-review/signoff", data=payload, headers={"Content-Type": "application/json"}, method="POST")
    with urlopen(request, timeout=30) as response:  # noqa: S310 - explicit local API
        print(response.read().decode("utf-8"))


if __name__ == "__main__":
    main()
