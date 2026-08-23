"""Optional Redis cache with fail-open semantics for the local learner path."""

from __future__ import annotations

import json
from typing import Any, Sequence

try:
    import redis.asyncio as redis_async
except ModuleNotFoundError:  # pragma: no cover
    redis_async = None  # type: ignore[assignment]


class RedisCache:
    def __init__(self, url: str, *, enabled: bool = True, prefix: str = "opensupport:"):
        self.enabled = enabled and redis_async is not None
        self.prefix = prefix
        self.client = redis_async.from_url(url, socket_connect_timeout=1.0) if self.enabled else None

    def key(self, raw: str) -> str:
        return f"{self.prefix}{raw}"

    async def get_many(self, keys: Sequence[str]) -> dict[str, Any]:
        if not self.enabled or self.client is None or not keys:
            return {}
        try:
            values = await self.client.mget([self.key(key) for key in keys])
            result: dict[str, Any] = {}
            for key, value in zip(keys, values, strict=True):
                if value is None:
                    continue
                if isinstance(value, bytes):
                    value = value.decode("utf-8")
                result[key] = json.loads(value)
            return result
        except Exception:
            return {}

    async def set_many(self, values: dict[str, Any], ttl: int) -> None:
        if not self.enabled or self.client is None or not values:
            return
        try:
            pipe = self.client.pipeline()
            for key, value in values.items():
                pipe.set(self.key(key), json.dumps(value, ensure_ascii=False), ex=max(1, ttl))
            await pipe.execute()
        except Exception:
            return

    async def close(self) -> None:
        if self.client is not None:
            await self.client.aclose()
