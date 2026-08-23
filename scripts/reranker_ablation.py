"""Run a bounded V0.4 reranker ablation on one frozen benchmark slice.

This script deliberately constructs a fresh RagService per configuration so
candidate-k, batch size and text truncation are measured independently. It is
an experiment runner, not a way to silently change the default production
assembly.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.config import get_settings
from app.eval import load_benchmark_cases
from app.rag import RagService

ROOT = Path(__file__).resolve().parent.parent
REPORT = ROOT / "reports" / "reranker_ablation_latest.json"


async def run_configuration(config: dict[str, int], *, benchmark_version: str, max_cases: int) -> dict[str, Any]:
    base = get_settings()
    settings = base.model_copy(update={
        "reranker_enabled": True,
        "reranker_provider": "llama_cpp",
        "reranker_candidate_k": config["candidate_k"],
        "reranker_batch_size": config["batch_size"],
        "reranker_text_chars": config["text_chars"],
    })
    rag = RagService(settings)
    try:
        _, cases = load_benchmark_cases(ROOT / "evals" / f"customer_support_benchmark_{benchmark_version}.json")
        cases = cases[:max_cases]
        rows: list[dict[str, Any]] = []
        for case in cases:
            trace: list[Any] = []
            started = time.perf_counter()
            hits = await rag.retrieve(case["question"], top_k=3, trace=trace, retrieval_mode="hybrid", assembly_version="v0_4")
            elapsed = round((time.perf_counter() - started) * 1000, 2)
            rank = next((index for index, hit in enumerate(hits, start=1) if hit.source_url in case["expected_urls"]), None)
            rerank_trace = next((item for item in trace if item.name == "rerank_candidates" and item.status == "completed"), None)
            rows.append({
                "case_id": case["case_id"],
                "hit": rank is not None,
                "rank": rank,
                "reciprocal_rank": round(1 / rank, 4) if rank else 0.0,
                "latency_ms": elapsed,
                "rerank": rerank_trace.details if rerank_trace else {},
            })
        latencies = sorted(row["latency_ms"] for row in rows)
        p95 = latencies[min(len(latencies) - 1, max(0, int(len(latencies) * 0.95) - 1))] if latencies else 0.0
        return {
            "config": config,
            "case_count": len(rows),
            "hit_at_3": round(sum(row["hit"] for row in rows) / len(rows), 4) if rows else 0.0,
            "mrr": round(sum(row["reciprocal_rank"] for row in rows) / len(rows), 4) if rows else 0.0,
            "retrieval_p95_ms": p95,
            "retrieval_mean_ms": round(sum(latencies) / len(latencies), 2) if latencies else 0.0,
            "cases": rows,
        }
    finally:
        await rag.close()


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark-version", default="v0.2", choices=["v0.2", "v0.3"])
    parser.add_argument("--max-cases", type=int, default=8, choices=range(1, 51))
    parser.add_argument("--candidate-k", type=int, nargs="+", default=[20, 50])
    args = parser.parse_args()
    configs = [
        {"candidate_k": candidate_k, "batch_size": batch_size, "text_chars": text_chars}
        for candidate_k, batch_size, text_chars in [
            (candidate_k, 16, 800) for candidate_k in args.candidate_k
        ]
    ]
    results = []
    for config in configs:
        results.append(await run_configuration(config, benchmark_version=args.benchmark_version, max_cases=args.max_cases))
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "benchmark_version": f"customer-support-{args.benchmark_version}-seed",
        "frozen_case_count": args.max_cases,
        "default_chain_unchanged": True,
        "results": results,
        "decision_rule": "只在同集 MRR/nDCG 或 Citation Support 稳定改善且 p95/资源预算可接受时晋级；否则保留为实验组件。",
    }
    REPORT.parent.mkdir(exist_ok=True)
    REPORT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
