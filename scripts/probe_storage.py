from __future__ import annotations

import asyncio

import psycopg

from app.config import get_settings
from app.storage import SourceOfTruthStore


async def main() -> None:
    settings = get_settings()
    store = SourceOfTruthStore(settings)
    print("dsn", store.postgres_dsn)
    try:
        async with await psycopg.AsyncConnection.connect(store.postgres_dsn, connect_timeout=1) as conn:
            await conn.execute("SELECT 1")
        print("postgres direct: ready")
    except Exception as exc:
        print("postgres direct:", type(exc).__name__, str(exc))
    print("health", await store.health())


if __name__ == "__main__":
    asyncio.run(main())
