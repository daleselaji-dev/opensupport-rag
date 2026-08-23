"""Deterministic V0.7 Graph profile smoke/evidence check."""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent.parent
REPORT = ROOT / "reports" / "graph_eval_latest.json"


def get_json(url: str) -> dict:
    request = Request(url, headers={"Accept": "application/json"})
    with urlopen(request, timeout=20) as response:  # noqa: S310 - explicit local benchmark URL
        return json.loads(response.read().decode("utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:18000")
    args = parser.parse_args()
    started = time.perf_counter()
    health = get_json(f"{args.url.rstrip('/')}/api/health")
    issue_result = get_json(f"{args.url.rstrip('/')}/api/graph/query?kind=top_issues&limit=10")
    product_result = get_json(f"{args.url.rstrip('/')}/api/graph/query?kind=top_products&limit=10")
    issues = issue_result.get("results", [])
    products = product_result.get("results", [])
    checks = {
        "graph_ready": health.get("graph", {}).get("state") == "ready",
        "issues_non_empty": bool(issues) and all(int(item.get("complaint_count", 0)) > 0 for item in issues),
        "products_non_empty": bool(products) and all(int(item.get("complaint_count", 0)) > 0 for item in products),
        "no_negative_counts": all(int(item.get("complaint_count", 0)) >= 0 for item in issues + products),
    }
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "url": args.url,
        "checks": checks,
        "overall_passed": all(checks.values()),
        "latency_ms": round((time.perf_counter() - started) * 1000, 2),
        "top_issues": issues,
        "top_products": products,
        "limitations": [
            "这是结构化 Graph profile smoke，不是全局主题 Golden Set，也不证明因果、违法或责任。",
            "关系必须继续从 CFPB 结构化字段回溯到原始 Source。",
        ],
    }
    REPORT.parent.mkdir(exist_ok=True)
    REPORT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    raise SystemExit(0 if payload["overall_passed"] else 1)


if __name__ == "__main__":
    main()
