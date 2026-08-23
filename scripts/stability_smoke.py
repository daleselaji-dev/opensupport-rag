"""Repeat retrieval-only requests and produce a deterministic p50/p95 report."""

from __future__ import annotations

import argparse
import json
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent.parent


def post_json(url: str, payload: dict[str, object]) -> dict[str, object]:
    request = Request(url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"}, method="POST")
    with urlopen(request, timeout=120) as response:  # noqa: S310 - explicit local benchmark URL
        return json.loads(response.read().decode("utf-8"))


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    return ordered[min(len(ordered) - 1, max(0, int(len(ordered) * fraction) - 1))]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:18000")
    parser.add_argument("--iterations", type=int, default=10)
    parser.add_argument("--assembly", default="v0_5")
    args = parser.parse_args()
    question = "信用卡账单金额有错误，我需要按什么流程处理？"
    latencies: list[float] = []
    errors: list[str] = []
    for _ in range(max(1, args.iterations)):
        started = time.perf_counter()
        try:
            post_json(f"{args.url.rstrip('/')}/api/retrieve-preview", {"question": question, "retrieval_mode": "hybrid", "assembly_version": args.assembly})
            latencies.append(round((time.perf_counter() - started) * 1000, 2))
        except Exception as exc:  # benchmark records failures instead of hiding them
            errors.append(str(exc))
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "url": args.url,
        "assembly_version": args.assembly,
        "iterations": args.iterations,
        "successes": len(latencies),
        "errors": len(errors),
        "error_samples": errors[:3],
        "latency_ms": {
            "p50": round(percentile(latencies, .50), 2),
            "p95": round(percentile(latencies, .95), 2),
            "mean": round(statistics.mean(latencies), 2) if latencies else 0.0,
        },
        "error_rate": round(len(errors) / max(1, args.iterations), 4),
    }
    reports = ROOT / "reports"
    reports.mkdir(exist_ok=True)
    (reports / "stability_latest.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not errors else 2


if __name__ == "__main__":
    raise SystemExit(main())
