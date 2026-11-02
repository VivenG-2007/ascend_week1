"""Small in-memory sliding-window rate limiter (per process). Fine for a single-instance demo;
use a shared store such as Redis if you scale out."""
from __future__ import annotations

import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request

from app.config import get_settings

_hits: dict[tuple[str, str], deque[float]] = defaultdict(deque)


def reset() -> None:
    _hits.clear()


def limiter(bucket: str, per_minute_attr: str):
    def dep(request: Request) -> None:
        s = get_settings()
        if not s.rate_limit_enabled:
            return
        limit = getattr(s, per_minute_attr)
        ip = request.client.host if request.client else "unknown"
        q = _hits[(bucket, ip)]
        now = time.monotonic()
        while q and now - q[0] > 60:
            q.popleft()
        if len(q) >= limit:
            raise HTTPException(status_code=429, detail="Too many requests. Please slow down.", headers={"Retry-After": "30"})
        q.append(now)

    return dep


chat_limit = limiter("chat", "rate_limit_per_minute")
login_limit = limiter("login", "login_rate_limit_per_minute")
