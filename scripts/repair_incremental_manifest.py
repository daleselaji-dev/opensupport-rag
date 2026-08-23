"""Repair collection totals after an append-style ingestion."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from app.config import get_settings
from app.data_foundation import save_quality_report
from app.rag import RagService


async def main() -> None:
    settings = get_settings()
    data_dir = Path(settings.data_dir)
    quality_path = data_dir / "data_quality_latest.json"
    report = json.loads(quality_path.read_text(encoding="utf-8"))
    rag = RagService(settings)
    try:
        total = await rag.count()
    finally:
        await rag.close()
    batch = int(report.get("batch_indexed_documents") or report.get("accepted_documents") or 0)
    report["indexed_documents"] = total
    report["batch_indexed_documents"] = batch
    report.setdefault("stage_counts", {})["indexed"] = total
    report.setdefault("stage_counts", {})["active"] = total
    quality_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    manifest_path = data_dir / "ingest_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    manifest["indexed_documents"] = total
    manifest["batch_indexed_documents"] = batch
    manifest["collection_indexed_documents"] = total
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print({"status": "repaired", "batch_indexed_documents": batch, "collection_indexed_documents": total})


if __name__ == "__main__":
    asyncio.run(main())
