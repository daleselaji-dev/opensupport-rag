"""Remove only duplicate Chunk IDs identified by the V0.0 quality report."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from qdrant_client import AsyncQdrantClient

from app.config import get_settings


async def main() -> None:
    settings = get_settings()
    report = json.loads((Path(settings.data_dir) / "data_quality_latest.json").read_text(encoding="utf-8"))
    duplicate_ids = set(report.get("duplicate_chunk_ids", []))
    if not duplicate_ids:
        print({"status": "nothing_to_do"})
        return
    client = AsyncQdrantClient(url=settings.qdrant_url, check_compatibility=False, trust_env=False)
    try:
        deleted: dict[str, list[str]] = {}
        for collection in [settings.collection_name, settings.sparse_collection_name]:
            if not await client.collection_exists(collection):
                continue
            points, _ = await client.scroll(collection_name=collection, limit=10000, with_payload=True, with_vectors=False)
            target_ids = [point.id for point in points if str((point.payload or {}).get("chunk_id", "")) in duplicate_ids]
            if target_ids:
                await client.delete(collection_name=collection, points_selector=target_ids, wait=True)
            deleted[collection] = [str(point_id) for point_id in target_ids]
        print({"status": "deduplicated", "duplicate_chunk_ids": sorted(duplicate_ids), "deleted": deleted})
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
