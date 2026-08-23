"""Deterministic retrieval evaluation for the OpenSupport workbench.

The seed set is authored against real CFPB URLs. It evaluates retrieval only;
it deliberately does not use an LLM judge, so a slow or unavailable chat model
cannot hide a retrieval regression.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.schemas import EvalCaseResult, EvalGate, EvalSummary

ROOT = Path(__file__).resolve().parent.parent
REPORTS = ROOT / "reports"
BENCHMARK_PATH = ROOT / "evals" / "customer_support_benchmark_v0.2.json"
BENCHMARK_PATHS = {
    "v0_2": BENCHMARK_PATH,
    "v0_3": ROOT / "evals" / "customer_support_benchmark_v0.3.json",
}

GOLDEN_CASES: list[dict[str, Any]] = [
    {
        "case_id": "unauthorized-card-zh",
        "question": "我发现信用卡有一笔陌生扣款，应该怎样提出争议？",
        "expected_urls": [
            "https://www.consumerfinance.gov/ask-cfpb/how-do-i-dispute-a-charge-on-my-credit-card-bill-en-61/",
            "https://www.consumerfinance.gov/ask-cfpb/what-is-an-unauthorized-use-of-a-credit-card-en-26/",
        ],
    },
    {
        "case_id": "unauthorized-card-en",
        "question": "I do not recognize a credit card transaction. What information should I gather before disputing it?",
        "expected_urls": [
            "https://www.consumerfinance.gov/ask-cfpb/how-do-i-dispute-a-charge-on-my-credit-card-bill-en-61/",
            "https://www.consumerfinance.gov/ask-cfpb/what-is-an-unauthorized-use-of-a-credit-card-en-26/",
        ],
    },
    {
        "case_id": "billing-error-zh",
        "question": "信用卡账单金额有错误，我需要按什么流程处理？",
        "expected_urls": [
            "https://www.consumerfinance.gov/consumer-tools/credit-cards/how-to-fix-mistakes-in-your-credit-card-bill/",
            "https://www.consumerfinance.gov/rules-policy/regulations/1026/13/",
        ],
    },
    {
        "case_id": "billing-error-en",
        "question": "What should I do when a credit card billing error appears on my statement?",
        "expected_urls": [
            "https://www.consumerfinance.gov/consumer-tools/credit-cards/how-to-fix-mistakes-in-your-credit-card-bill/",
            "https://www.consumerfinance.gov/rules-policy/regulations/1026/13/",
        ],
    },
    {
        "case_id": "reg-z-en",
        "question": "Which official rule describes the billing error resolution process for a credit card?",
        "expected_urls": ["https://www.consumerfinance.gov/rules-policy/regulations/1026/13/"],
    },
    {
        "case_id": "complaint-process-zh",
        "question": "我想向 CFPB 提交消费投诉，官方流程是什么？",
        "expected_urls": ["https://www.consumerfinance.gov/complaint/process/"],
    },
    {
        "case_id": "company-process-en",
        "question": "How does a company receive and respond to a CFPB consumer complaint?",
        "expected_urls": ["https://www.consumerfinance.gov/compliance/consumer-complaint-program/company-process/"],
    },
    {
        "case_id": "complaint-process-en",
        "question": "What happens after a consumer submits a complaint to the CFPB?",
        "expected_urls": ["https://www.consumerfinance.gov/complaint/process/"],
    },
]


def load_benchmark_cases(path: Path = BENCHMARK_PATH) -> tuple[str, list[dict[str, Any]]]:
    """Load answerable retrieval cases from the versioned domain Benchmark.

    Refusal/safety cases stay in the same dataset but are evaluated by the
    generation/safety harness, not counted as retrieval hits.
    """

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        benchmark_version = str(payload.get("benchmark_version", path.stem))
        cases = []
        for case in payload.get("cases", []):
            expected_urls = case.get("expected_source_urls", case.get("expected_urls", []))
            if case.get("expected_action", "answer") != "answer" or not expected_urls:
                continue
            cases.append(
                {
                    **case,
                    "expected_urls": expected_urls,
                    "slices": case.get("slices", []),
                    "required_source_types": case.get("required_source_types", []),
                }
            )
        if cases:
            return benchmark_version, cases
    except (OSError, json.JSONDecodeError, TypeError):
        pass
    return "legacy-hardcoded", GOLDEN_CASES


def _source_summary(hit: Any) -> dict[str, Any]:
    return {
        "citation": hit.citation,
        "source_type": hit.source_type,
        "title": hit.title,
        "source_url": hit.source_url,
        "score": hit.score,
    }


def render_markdown(summary: EvalSummary) -> str:
    lines = [
        f"# OpenSupport Retrieval Eval ({summary.version})",
        "",
        f"- Evaluated at: `{summary.evaluated_at}`",
        f"- Collection: `{summary.collection_name}`",
        f"- Embedding: `{summary.embedding_model}`",
        f"- Assembly version: `{summary.assembly_version}`",
        f"- Retrieval mode: `{summary.retrieval_mode}`",
        f"- Benchmark: `{summary.benchmark_version}`",
        f"- Overall: **{'PASS' if summary.overall_passed else 'FAIL'}**",
        "",
        "## Index inventory",
        "",
    ]
    for key, value in summary.index_inventory.items():
        lines.append(f"- {key}: `{value}`")
    lines += ["", "## Metrics", ""]
    for key, value in summary.metrics.items():
        lines.append(f"- {key}: `{value}`")
    lines += ["", "## Gates", "", "| Gate | Actual | Target | Status | Note |", "|---|---:|---:|---|---|"]
    for gate in summary.gates:
        lines.append(f"| {gate.label} | {gate.actual} | {gate.target} | {'PASS' if gate.passed else 'FAIL'} | {gate.note} |")
    lines += ["", "## Cases", "", "| Case | Slice | Hit@k | Rank | Retrieval ms | Top source URLs |", "|---|---|---|---:|---:|---|"]
    for case in summary.cases:
        urls = ", ".join(source["source_url"] for source in case.top_sources)
        lines.append(f"| {case.case_id} | {', '.join(case.slices)} | {'yes' if case.hit else 'no'} | {case.rank or '-'} | {case.retrieval_ms} | {urls} |")
    lines += ["", "## Limitations", ""]
    lines.extend(f"- {item}" for item in summary.limitations)
    return "\n".join(lines) + "\n"


async def run_retrieval_eval(
    rag: Any,
    retrieval_mode: str = "dense",
    assembly_version: str = "v0_3",
    benchmark_version: str = "v0_2",
) -> EvalSummary:
    inventory = await rag.index_inventory()
    benchmark_path = BENCHMARK_PATHS.get(benchmark_version, BENCHMARK_PATH)
    benchmark_version_label, benchmark_cases = load_benchmark_cases(benchmark_path)
    case_results: list[EvalCaseResult] = []
    for case in benchmark_cases:
        trace: list[Any] = []
        started = rag.clock()
        hits = await rag.retrieve(case["question"], top_k=3, trace=trace, retrieval_mode=retrieval_mode, assembly_version=assembly_version)
        elapsed = round((rag.clock() - started) * 1000, 2)
        rank = next(
            (index for index, hit in enumerate(hits, start=1) if hit.source_url in case["expected_urls"]),
            None,
        )
        required_types = list(case.get("required_source_types", []))
        required_types_hit = all(any(hit.source_type == source_type for hit in hits) for source_type in required_types)
        case_results.append(
            EvalCaseResult(
                case_id=case["case_id"],
                question=case["question"],
                expected_urls=case["expected_urls"],
                hit=rank is not None,
                rank=rank,
                reciprocal_rank=round(1 / rank, 4) if rank else 0.0,
                retrieval_ms=elapsed,
                top_sources=[_source_summary(hit) for hit in hits],
                trace=trace,
                slices=list(case.get("slices", [])),
                expected_action=str(case.get("expected_action", "answer")),
                required_source_types=required_types,
                required_source_types_hit=required_types_hit,
            )
        )

    total = len(case_results)
    hit_rate = round(sum(case.hit for case in case_results) / total, 4) if total else 0.0
    mrr = round(sum(case.reciprocal_rank for case in case_results) / total, 4) if total else 0.0
    retrieval_times = sorted(case.retrieval_ms for case in case_results)
    p95_index = min(total - 1, max(0, int(total * 0.95) - 1)) if total else 0
    p95 = retrieval_times[p95_index] if retrieval_times else 0.0
    slice_metrics: dict[str, dict[str, float | int]] = {}
    all_slices = sorted({slice_name for case in case_results for slice_name in case.slices})
    for slice_name in all_slices:
        subset = [case for case in case_results if slice_name in case.slices]
        slice_metrics[slice_name] = {
            "case_count": len(subset),
            "hit_at_3": round(sum(case.hit for case in subset) / len(subset), 4) if subset else 0.0,
            "mrr": round(sum(case.reciprocal_rank for case in subset) / len(subset), 4) if subset else 0.0,
        }
    gates = [
        EvalGate(
            key="unique_complaints",
            label="唯一投诉案例数",
            actual=inventory["complaint_chunks"],
            target=200,
            passed=inventory["complaint_chunks"] >= 200,
            note="V0.1 真实数据门；当前不足时不能宣称 200 条验收通过。",
        ),
        EvalGate(
            key="manifest_consistency",
            label="Manifest 与真实点数一致",
            actual=inventory["manifest_indexed_documents"],
            target=inventory["qdrant_points"],
            passed=inventory["manifest_indexed_documents"] == inventory["qdrant_points"],
            note="清单必须能够复现真实索引，而不是只记录请求数量。",
        ),
        EvalGate(
            key="retrieval_hit_at_3",
            label="真实来源 Hit@3",
            actual=hit_rate,
            target=0.75,
            passed=hit_rate >= 0.75,
            note="仅评估检索，不把生成模型质量混入。",
        ),
        EvalGate(
            key="mrr",
            label="真实来源 MRR",
            actual=mrr,
            target=0.6,
            passed=mrr >= 0.6,
            note="正确来源越靠前，MRR 越高。",
        ),
        EvalGate(
            key="official_evidence",
            label="官方证据存在",
            actual=inventory["official_chunks"],
            target=1,
            passed=inventory["official_chunks"] >= 1,
            note="没有官方指导时，系统不能回答流程性问题。",
        ),
    ]
    summary = EvalSummary(
        version=f"{assembly_version}-seed-{retrieval_mode}",
        retrieval_mode=retrieval_mode,
        assembly_version=assembly_version,
        evaluated_at=datetime.now(timezone.utc).isoformat(),
        collection_name=rag.settings.collection_name,
        embedding_model=rag.settings.embedding_model,
        benchmark_version=benchmark_version_label,
        index_inventory=inventory,
        metrics={
            "case_count": total,
            "answerable_case_count": total,
            "hit_at_3": hit_rate,
            "mrr": mrr,
            "retrieval_p95_ms": p95,
            "retrieval_mean_ms": round(sum(retrieval_times) / total, 2) if total else 0.0,
            "slice_metrics": slice_metrics,
        },
        gates=gates,
        cases=case_results,
        overall_passed=all(gate.passed for gate in gates),
        limitations=[
            f"当前使用 Benchmark {benchmark_version_label} 的 {total} 条可回答检索案例；拒答/安全案例由生成安全 Eval 单独统计。",
            "当前只测确定性的检索命中、排名、数据一致性和延迟；回答完整性、拒答和安全性要在生成模型稳定后单独评估。",
            "投诉文本是消费者主张，命中投诉不代表事实成立或公司违法。",
        ],
    )
    REPORTS.mkdir(exist_ok=True)
    (REPORTS / f"eval_latest_{assembly_version}_{retrieval_mode}.json").write_text(summary.model_dump_json(indent=2), encoding="utf-8")
    (REPORTS / f"eval_latest_{assembly_version}_{retrieval_mode}.md").write_text(render_markdown(summary), encoding="utf-8")
    (REPORTS / "eval_latest.json").write_text(summary.model_dump_json(indent=2), encoding="utf-8")
    (REPORTS / "eval_latest.md").write_text(render_markdown(summary), encoding="utf-8")
    return summary


def load_last_eval() -> dict[str, Any] | None:
    path = REPORTS / "eval_latest.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
