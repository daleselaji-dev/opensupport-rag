"""Checkpointed ingestion for the official CFPB bulk narrative snapshot.

Unlike the learning `/api/ingest-local` path, this worker embeds and upserts
bounded batches, skips already indexed chunk IDs, and writes a progress report
so a long local build can be inspected and resumed safely.
"""

from __future__ import annotations

import argparse
import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path

from app.cfpb import fetch_official_guidance, load_cfpb_official_bulk_csv
from app.config import get_settings
from app.data_foundation import finalize_quality_report, prepare_documents, save_quality_report
from app.rag import RagService
from app.schemas import SourceDocument
from app.storage import SourceOfTruthStore

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
PROGRESS = DATA / "bulk_ingest_progress.json"
FAILURE = DATA / "bulk_ingest_failure_latest.json"


async def existing_chunk_ids(rag: RagService) -> set[str]:
    found: set[str] = set()
    offset = None
    while True:
        points, offset = await rag.qdrant.scroll(
            collection_name=rag.settings.collection_name,
            offset=offset,
            limit=512,
            with_payload=True,
            with_vectors=False,
        )
        found.update(str((point.payload or {}).get("chunk_id")) for point in points if (point.payload or {}).get("chunk_id"))
        if offset is None:
            return found


def save_progress(payload: dict[str, object]) -> None:
    DATA.mkdir(exist_ok=True)
    PROGRESS.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--filename", default="cfpb_official_narratives_12000.csv")
    parser.add_argument("--limit", type=int, default=12000)
    parser.add_argument("--batch-size", type=int, default=256)
    args = parser.parse_args()
    settings = get_settings()
    rag = RagService(settings)
    storage = SourceOfTruthStore(settings)
    started = datetime.now(timezone.utc).isoformat()
    try:
        raw_path = DATA / "raw" / args.filename
        complaints = load_cfpb_official_bulk_csv(str(raw_path), args.limit)
        guidance, guidance_failures = await fetch_official_guidance()
        if not guidance:
            raise RuntimeError(f"官方指导页面全部失败：{guidance_failures}")
        raw_documents = [record.to_document() for record in complaints] + guidance
        documents, quality = prepare_documents(raw_documents)
        already_indexed = await existing_chunk_ids(rag)
        new_documents = [document for document in documents if document.chunk_id not in already_indexed]
        skipped = len(documents) - len(new_documents)
        progress: dict[str, object] = {
            "status": "running",
            "started_at": started,
            "source_file": str(raw_path),
            "source_url": "https://files.consumerfinance.gov/ccdb/complaints.csv.zip",
            "requested_rows": args.limit,
            "accepted_documents": len(documents),
            "already_indexed": skipped,
            "new_documents": len(new_documents),
            "indexed_batches": 0,
            "indexed_new_documents": 0,
            "guidance_failures": guidance_failures,
        }
        save_progress(progress)
        for start in range(0, len(new_documents), args.batch_size):
            batch = new_documents[start : start + args.batch_size]
            indexed = await rag.ingest(batch)
            progress["indexed_batches"] = int(progress["indexed_batches"]) + 1
            progress["indexed_new_documents"] = int(progress["indexed_new_documents"]) + indexed
            progress["last_chunk_id"] = batch[-1].chunk_id if batch else None
            progress["updated_at"] = datetime.now(timezone.utc).isoformat()
            save_progress(progress)
            print(json.dumps({"batch": progress["indexed_batches"], "indexed": progress["indexed_new_documents"], "total": len(new_documents)}, ensure_ascii=False), flush=True)

        collection_indexed = await rag.count()
        quality = finalize_quality_report(quality, collection_indexed, len(new_documents), manifest_consistent=True)
        # Already-indexed IDs are an expected idempotency path, not a data
        # quality duplicate. Keep the count in the manifest/progress report;
        # the Data Quality duplicate gate only counts duplicates within the
        # incoming snapshot itself.
        manifest = {
            "source": "cfpb_official_bulk_csv",
            "source_url": "https://files.consumerfinance.gov/ccdb/complaints.csv.zip",
            "source_file": str(raw_path.relative_to(ROOT)),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "requested_rows": args.limit,
            "accepted_documents": len(documents),
            "new_documents": len(new_documents),
            "already_indexed": skipped,
            "indexed_documents": collection_indexed,
            "complaint_ids": [document.complaint_id for document in documents if document.complaint_id],
            "document_hashes": sorted(str(document.metadata.get("content_sha256")) for document in documents),
            "snapshot_id": quality.snapshot_id,
            "pipeline_version": quality.pipeline_version,
            "manifest_consistent": True,
        }
        (DATA / "ingest_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        save_quality_report(quality, DATA / "data_quality_latest.json")
        await storage.persist_ingestion(new_documents, quality, collection_indexed, settings.collection_name, settings.embedding_model)
        progress.update({"status": "completed", "completed_at": datetime.now(timezone.utc).isoformat(), "collection_indexed": collection_indexed, "manifest_consistent": True})
        save_progress(progress)
        print(json.dumps(progress, ensure_ascii=False, indent=2))
    except Exception as exc:
        failure = {"status": "failed", "failed_at": datetime.now(timezone.utc).isoformat(), "error": str(exc), "progress": json.loads(PROGRESS.read_text(encoding="utf-8")) if PROGRESS.exists() else {}}
        FAILURE.write_text(json.dumps(failure, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        raise
    finally:
        await rag.close()


if __name__ == "__main__":
    asyncio.run(main())
