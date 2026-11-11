import threading
import time
from collections import deque

import httpx

from app.config import get_settings


class RateLimiter:
    """Thread-safe sliding-window limiter: at most `max_calls` per `period` seconds."""

    def __init__(self, max_calls: int, period: float):
        self.max_calls = max_calls
        self.period = period
        self._calls: deque[float] = deque()
        self._lock = threading.Lock()

    def acquire(self) -> None:
        while True:
            with self._lock:
                now = time.monotonic()
                while self._calls and now - self._calls[0] >= self.period:
                    self._calls.popleft()
                if len(self._calls) < self.max_calls:
                    self._calls.append(now)
                    return
                wait = self.period - (now - self._calls[0])
            time.sleep(max(wait, 0.01))


# Limits from provider docs: SEC 10 req/s, Finnhub free 60/min, PatentsView 45/min.
LIMITERS = {
    "sec": RateLimiter(8, 1.0),
    "finnhub": RateLimiter(55, 60.0),
    "patentsview": RateLimiter(40, 60.0),
    "wikidata": RateLimiter(5, 1.0),
}


def client(user_agent: str | None = None, timeout: float = 30.0) -> httpx.Client:
    settings = get_settings()
    ua = user_agent or settings.http_user_agent or f"Investar/0.1 ({settings.sec_user_agent})"
    return httpx.Client(
        headers={"User-Agent": ua, "Accept-Encoding": "gzip, deflate"},
        timeout=timeout,
        follow_redirects=True,
    )
