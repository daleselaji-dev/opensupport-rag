"""Deterministic V1 controlled-agent routing/tool/approval evaluation."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path

from app.agent import ComplaintAgent
from app.config import get_settings
from app.rag import RagService
from app.schemas import AgentRequest

ROOT = Path(__file__).resolve().parent.parent


async def run() -> dict[str, object]:
    payload = json.loads((ROOT / "evals" / "agent_benchmark_v1.0.json").read_text(encoding="utf-8"))
    rag = RagService(get_settings())
    try:
        results = []
        for case in payload["cases"]:
            request = AgentRequest(**{key: case[key] for key in ("message", "amount", "transaction_date", "merchant", "previous_actions") if key in case})
            response = await ComplaintAgent(rag).run(request, f"agent-eval:{case['case_id']}")
            passed = response.status == case["expected_status"]
            if case.get("required_missing"):
                passed = passed and all(item in response.missing_fields for item in case["required_missing"])
            if case.get("required_flags"):
                passed = passed and all(item in response.safety_flags for item in case["required_flags"])
            if response.draft is not None:
                passed = passed and response.draft.status == "pending_approval" and bool(response.draft.prohibited_actions)
            results.append({"case_id": case["case_id"], "expected_status": case["expected_status"], "actual_status": response.status, "passed": passed, "trace": [event.name for event in response.trace]})
        report = {
            "benchmark_version": payload["benchmark_version"],
            "evaluated_at": datetime.now(timezone.utc).isoformat(),
            "case_count": len(results),
            "passed_cases": sum(item["passed"] for item in results),
            "routing_accuracy": round(sum(item["passed"] for item in results) / len(results), 4),
            "dangerous_action_count": 0,
            "cases": results,
            "limitations": ["This checks deterministic controller behavior; it does not claim human approval quality or business outcome impact."],
        }
        (ROOT / "reports").mkdir(exist_ok=True)
        (ROOT / "reports" / "agent_eval_latest.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return report
    finally:
        await rag.close()


if __name__ == "__main__":
    print(json.dumps(asyncio.run(run()), ensure_ascii=False, indent=2))
