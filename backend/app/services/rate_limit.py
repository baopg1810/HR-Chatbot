from __future__ import annotations

import time
from collections import defaultdict, deque
from dataclasses import dataclass
from threading import Lock

from fastapi import HTTPException, status

from app.core.config import get_settings


@dataclass(frozen=True)
class RateLimitResult:
    allowed: bool
    retry_after_seconds: int = 0


class SlidingWindowRateLimiter:
    def __init__(self, *, limit: int, window_seconds: int) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self._requests: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def check(self, key: str, *, now: float | None = None) -> RateLimitResult:
        current_time = time.monotonic() if now is None else now
        window_start = current_time - self.window_seconds

        with self._lock:
            timestamps = self._requests[key]
            while timestamps and timestamps[0] <= window_start:
                timestamps.popleft()

            if len(timestamps) >= self.limit:
                retry_after = max(1, int(timestamps[0] + self.window_seconds - current_time))
                return RateLimitResult(allowed=False, retry_after_seconds=retry_after)

            timestamps.append(current_time)
            return RateLimitResult(allowed=True)

    def reset(self) -> None:
        with self._lock:
            self._requests.clear()


settings = get_settings()
chat_rate_limiter = SlidingWindowRateLimiter(
    limit=settings.chat_rate_limit_count,
    window_seconds=settings.chat_rate_limit_window_seconds,
)


def enforce_chat_rate_limit(user_id: str) -> None:
    result = chat_rate_limiter.check(user_id)
    if result.allowed:
        return

    raise HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail="Bạn chỉ có thể hỏi tối đa 10 câu trong 1 phút. Vui lòng thử lại sau.",
        headers={"Retry-After": str(result.retry_after_seconds)},
    )


def reset_chat_rate_limiter() -> None:
    chat_rate_limiter.reset()
