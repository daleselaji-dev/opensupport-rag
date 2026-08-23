"""One-shot probe for Qdrant native multilingual BM25 inference."""

from __future__ import annotations

import asyncio

from qdrant_client import AsyncQdrantClient, models


async def main() -> None:
    client = AsyncQdrantClient(url="http://localhost:16333", check_compatibility=False)
    name = "opensupport_sparse_probe"
    try:
        await client.recreate_collection(
            collection_name=name,
            vectors_config={"dense": models.VectorParams(size=3, distance=models.Distance.COSINE)},
            sparse_vectors_config={"sparse": models.SparseVectorParams(modifier=models.Modifier.IDF)},
        )
        await client.upsert(
            collection_name=name,
            points=[
                models.PointStruct(
                    id=1,
                    vector={
                        "dense": [0.1, 0.2, 0.3],
                        "sparse": models.Document(text="hello world", model="qdrant/bm25"),
                    },
                    payload={"text": "hello world"},
                )
            ],
            wait=True,
        )
        result = await client.query_points(
            collection_name=name,
            query=models.Document(text="hello", model="qdrant/bm25"),
            using="sparse",
            limit=1,
        )
        print({"status": "ok", "hits": len(result.points)})
    finally:
        await client.delete_collection(name)
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
