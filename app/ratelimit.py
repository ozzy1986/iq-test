"""Ограничение частоты запросов по IP: скользящее окно в памяти процесса.

Достаточно для одного воркера. При нескольких воркерах/серверах счётчики нужно
вынести в общий стор (Redis) — интерфейс `limit()` при этом не меняется.
"""
import time
from collections import deque

from fastapi import Depends, HTTPException, Request

WINDOW = 60.0
MAX_KEYS = 20_000


class RateLimiter:
    def __init__(self) -> None:
        self.hits: dict[tuple[str, str], deque[float]] = {}

    def check(self, bucket: str, key: str, limit: int) -> None:
        now = time.monotonic()
        queue = self.hits.setdefault((bucket, key), deque())
        while queue and queue[0] <= now - WINDOW:
            queue.popleft()
        if len(queue) >= limit:
            retry = max(1, int(queue[0] + WINDOW - now) + 1)
            raise HTTPException(429, "Слишком много запросов. Попробуйте через минуту.",
                                headers={"Retry-After": str(retry)})
        queue.append(now)
        if len(self.hits) > MAX_KEYS:  # не даём словарю расти бесконечно
            self.hits = {k: q for k, q in self.hits.items() if q and q[-1] > now - WINDOW}

    def reset(self) -> None:
        self.hits.clear()


limiter = RateLimiter()


def limit(bucket: str, per_minute: int):
    """Зависимость FastAPI: не больше `per_minute` запросов в минуту с одного IP."""

    def dependency(request: Request) -> None:
        limiter.check(bucket, request.client.host if request.client else "unknown", per_minute)

    return Depends(dependency)
