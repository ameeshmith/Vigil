import time
import asyncio
from typing import Any, Optional, Dict, Tuple

class TTLCache:
    """Thread-safe in-memory cache with Time-To-Live (TTL) expiration."""
    def __init__(self, default_ttl: float = 300.0, max_entries: int = 1000):
        self.default_ttl = default_ttl
        self.max_entries = max_entries
        self._cache: Dict[str, Tuple[float, Any]] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[Any]:
        async with self._lock:
            entry = self._cache.get(key)
            if not entry:
                return None
            expire_at, value = entry
            if time.time() > expire_at:
                del self._cache[key]
                return None
            return value

    async def set(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        async with self._lock:
            if len(self._cache) >= self.max_entries:
                # Evict expired entries
                now = time.time()
                keys_to_delete = [k for k, (exp, _) in self._cache.items() if now > exp]
                for k in keys_to_delete:
                    del self._cache[k]
                # If still over capacity, remove oldest 20%
                if len(self._cache) >= self.max_entries:
                    excess = len(self._cache) - int(self.max_entries * 0.8)
                    for k in list(self._cache.keys())[:excess]:
                        del self._cache[k]

            expires = time.time() + (ttl if ttl is not None else self.default_ttl)
            self._cache[key] = (expires, value)

    async def clear(self) -> None:
        async with self._lock:
            self._cache.clear()

class TokenBucketRateLimiter:
    """Token bucket rate limiter for external APIs."""
    def __init__(self, rate: float = 10.0, capacity: float = 15.0):
        """
        :param rate: tokens added per second
        :param capacity: maximum burst capacity
        """
        self.rate = rate
        self.capacity = capacity
        self.tokens = capacity
        self.last_check = time.time()
        self._lock = asyncio.Lock()

    async def acquire(self, tokens: float = 1.0) -> bool:
        async with self._lock:
            now = time.time()
            elapsed = now - self.last_check
            self.last_check = now
            self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)

            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False

    async def wait_for_token(self, tokens: float = 1.0, timeout: float = 10.0) -> bool:
        start = time.time()
        while time.time() - start < timeout:
            if await self.acquire(tokens):
                return True
            await asyncio.sleep(0.1)
        return False

