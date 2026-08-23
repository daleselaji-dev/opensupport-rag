"""Migrate the current Dense collection into the named Dense+Sparse collection."""

from __future__ import annotations

import asyncio

from app.config import get_settings
from app.rag import RagService


async def main() -> None:
    rag = RagService(get_settings())
    try:
        migrated = await rag.migrate_existing_to_sparse()
        print({"status": "ready", "migrated_documents": migrated, "collection": rag.settings.sparse_collection_name})
    finally:
        await rag.close()


if __name__ == "__main__":
    asyncio.run(main())
