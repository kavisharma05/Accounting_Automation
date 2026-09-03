"""Simple in-memory rate limiter for webhook endpoints."""

import time
from collections import defaultdict


class RateLimiter:
    def __init__(self, max_requests: int, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._hits: dict[str, list[float]] = defaultdict(list)

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        window_start = now - self.window_seconds
        hits = [t for t in self._hits[key] if t > window_start]
        if len(hits) >= self.max_requests:
            self._hits[key] = hits
            return False
        hits.append(now)
        self._hits[key] = hits
        return True


_webhook_limiter: RateLimiter | None = None


def get_webhook_limiter(max_per_minute: int) -> RateLimiter:
    global _webhook_limiter
    if _webhook_limiter is None:
        _webhook_limiter = RateLimiter(max_requests=max_per_minute, window_seconds=60)
    return _webhook_limiter
