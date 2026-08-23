"""Small in-process sliding-window limiter for the public local API.

Production deployments should put a shared gateway/Redis limiter in front of
multiple replicas; this local limiter still prevents an accidental browser
loop from saturating LM Studio and makes the behavior visible in tests.
"""

from __future__ import annotations

import time
from collections import defaultdict, deque


class SlidingWindowLimiter:
    def __init__(self, limit: int, window_s: float = 60.0):
        self.limit = max(1, limit)
        self.window_s = window_s
        self._events: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str) -> tuple[bool, int]:
        now = time.monotonic()
        events = self._events[key]
        while events and now - events[0] >= self.window_s:
            events.popleft()
        if len(events) >= self.limit:
            retry_after = max(1, int(self.window_s - (now - events[0])))
            return False, retry_after
        events.append(now)
        return True, 0
