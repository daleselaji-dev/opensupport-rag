"""Scan the active Qdrant payloads for PII and indirect prompt injection."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from app.config import get_settings
from app.rag import RagService
from app.security import scan_text

ROOT = Path(__file__).resolve().parent.parent


async def run() -> dict[str, object]:
    rag = RagService(get_settings())
    try:
        collection, _ = rag.index_registry.active()
        points, offset = [], None
        while True:
            batch, offset = await rag.qdrant.scroll(collection_name=collection, offset=offset, limit=256, with_payload=True, with_vectors=False)
            points.extend(batch)
            if offset is None:
                break
        findings = []
        for point in points:
            payload = dict(point.payload or {})
            scan = scan_text(str(payload.get("text", "")))
            if not scan["safe"]:
                findings.append({"chunk_id": payload.get("chunk_id", str(point.id)), "source_type": payload.get("source_type"), **scan})
        report = {
            "collection": collection,
            "scanned_points": len(points),
            "findings": len(findings),
            "pii_findings": sum(bool([flag for flag in item["pii_flags"] if flag != "phone" or item.get("source_type") == "complaint"]) for item in findings),
            "public_contact_patterns": sum(bool(item["pii_flags"]) and item.get("source_type") in {"guidance", "regulation"} for item in findings),
            "prompt_injection_findings": sum(bool(item["prompt_injection_flags"]) for item in findings),
            "isolated_prompt_injection_findings": sum(bool(item["prompt_injection_flags"]) and item.get("source_type") == "complaint" for item in findings),
            "unisolated_prompt_injection_findings": sum(bool(item["prompt_injection_flags"]) and item.get("source_type") != "complaint" for item in findings),
            "items": findings[:200],
        }
        (ROOT / "reports").mkdir(exist_ok=True)
        (ROOT / "reports" / "security_audit_latest.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return report
    finally:
        await rag.close()


if __name__ == "__main__":
    print(json.dumps(asyncio.run(run()), ensure_ascii=False, indent=2))
