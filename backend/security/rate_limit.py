"""Bounded single-instance rate limiting for the P1.5 staging service."""

from __future__ import annotations

import math
import threading
import time
from dataclasses import dataclass
from typing import Callable, Dict, Mapping, Optional, Tuple


DEFAULT_RATE_LIMITS = {
    "capture": 30,
    "retry": 10,
    "read": 120,
    "report": 10,
    "mutation": 30,
}


@dataclass(frozen=True)
class RateLimitDecision:
    allowed: bool
    limit: int
    remaining: int
    retry_after: int


class InMemoryRateLimiter:
    """Fixed-window limiter scoped to one process and one service instance."""

    def __init__(
        self,
        *,
        limits: Optional[Mapping[str, int]] = None,
        window_seconds: int = 60,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        configured = dict(DEFAULT_RATE_LIMITS if limits is None else limits)
        if set(configured) != set(DEFAULT_RATE_LIMITS):
            raise ValueError("rate limit buckets must match the supported routes")
        if any(not isinstance(value, int) or value < 1 for value in configured.values()):
            raise ValueError("rate limits must be positive integers")
        if not isinstance(window_seconds, int) or window_seconds < 1:
            raise ValueError("rate limit window must be a positive integer")
        self.limits = configured
        self.window_seconds = window_seconds
        self.clock = clock
        self._states: Dict[Tuple[str, str], Tuple[int, int]] = {}
        self._lock = threading.Lock()

    def consume(self, bucket: str, *, identity: str) -> RateLimitDecision:
        limit = self.limits[bucket]
        now = self.clock()
        window = int(now // self.window_seconds)
        state_key = (bucket, identity)
        with self._lock:
            stored_window, count = self._states.get(state_key, (window, 0))
            if stored_window != window:
                count = 0
            count += 1
            self._states[state_key] = (window, count)
        remaining = max(0, limit - count)
        retry_after = max(
            1,
            int(math.ceil(((window + 1) * self.window_seconds) - now)),
        )
        return RateLimitDecision(
            allowed=count <= limit,
            limit=limit,
            remaining=remaining,
            retry_after=retry_after,
        )


def route_bucket(method: str, path: str) -> Optional[str]:
    """Return the bounded policy bucket for one protected API route."""

    if not path.startswith("/api/v1/"):
        return None
    if method == "POST" and path == "/api/v1/capture":
        return "capture"
    if method == "POST" and path.endswith("/retry"):
        return "retry"
    if method == "POST" and path == "/api/v1/reports/preview":
        return "report"
    if method == "GET":
        return "read"
    return "mutation"
