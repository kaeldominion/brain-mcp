"""Per-client sliding-window rate limiting, enforced in-app.

Traefik's rate limits are per-IP and only cover remote traffic; local agents
on the Docker network bypass Traefik entirely, so the server enforces its own
per-token budget.
"""

from __future__ import annotations

import threading
import time
from collections import deque

from brain_mcp.errors import RateLimited

_WINDOW_SECONDS = 60.0


class RateLimiter:
    def __init__(self, requests_per_minute: int):
        self.rpm = requests_per_minute
        self._windows: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def check(self, client_name: str, now: float | None = None) -> None:
        if now is None:
            now = time.monotonic()
        with self._lock:
            window = self._windows.setdefault(client_name, deque())
            cutoff = now - _WINDOW_SECONDS
            while window and window[0] <= cutoff:
                window.popleft()
            if len(window) >= self.rpm:
                retry_after = window[0] + _WINDOW_SECONDS - now
                raise RateLimited(
                    f"rate limit exceeded ({self.rpm} requests/minute)",
                    retry_after_seconds=round(max(retry_after, 0.0), 2),
                )
            window.append(now)
