"""Backfill the existing verified Qdrant payloads into Postgres/MinIO.

This is a migration helper, not a replacement for an original-source ingest:
the MinIO artifact is explicitly labeled as a normalized snapshot.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from app.config import get_settings
from app.data_foundation import finalize_quality_report, prepare_documents, save_quality_report
from app.rag import RagService
from app.schemas import SourceDocument
from app.storage import SourceOfTruthStore


async def main() -> None:
    settings = get_settings()
    rag = RagService(settings)
    try:
        points = []
        offset = None
        while True:
            page, offset = await rag.qdrant.scroll(
                collection_name=settings.collection_name,
                offset=offset,
                limit=256,
                with_payload=True,
                with_vectors=False,
            )
            points.extend(page)
            if offset is None:
                break
        documents = [SourceDocument.model_validate(dict(point.payload or {})) for point in points]
        accepted, quality = prepare_documents(documents)
        quality = finalize_quality_report(quality, len(accepted))
        result = await SourceOfTruthStore(settings).persist_ingestion(
            accepted,
            quality,
            len(accepted),
            settings.collection_name,
            settings.embedding_model,
        )
        save_quality_report(quality, Path(settings.data_dir) / "data_quality_latest.json")
        Path(settings.data_dir, "ingest_manifest.json").write_text(
            json.dumps(
                {
                    "year": "backfill",
                    "requested_complaints": sum(document.source_type == "complaint" for document in accepted),
                    "complaint_ids": [document.complaint_id for document in accepted if document.complaint_id],
                    "guidance_urls": sorted({document.source_url for document in accepted if document.source_type != "complaint"}),
                    "indexed_documents": len(accepted),
                    "snapshot_id": quality.snapshot_id,
                    "pipeline_version": quality.pipeline_version,
                    "accepted_documents": quality.accepted_documents,
                    "duplicate_documents": quality.duplicate_documents,
                    "quarantined_documents": quality.quarantined_documents,
                    "document_hashes": sorted(str(document.metadata.get("content_sha256")) for document in accepted),
                    "storage": result,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        print(json.dumps({"points": len(points), "accepted": len(accepted), "quality": quality.model_dump(mode="json"), "storage": result}, ensure_ascii=False))
    finally:
        await rag.close()


if __name__ == "__main__":
    asyncio.run(main())
