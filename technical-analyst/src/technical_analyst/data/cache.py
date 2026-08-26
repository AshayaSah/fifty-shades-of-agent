import time
from threading import Lock


class TTLCache:
    """Simple in-process TTL cache. Not shared across processes —
    this only exists to avoid duplicate provider calls within a single
    running MCP server, on top of the DB-backed history."""

    def __init__(self, ttl_seconds: int):
        self.ttl = ttl_seconds
        self._store: dict[str, tuple[float, object]] = {}
        self._lock = Lock()

    def get(self, key: str):
        with self._lock:
            entry = self._store.get(key)
            if not entry:
                return None
            ts, value = entry
            if time.time() - ts > self.ttl:
                del self._store[key]
                return None
            return value

    def set(self, key: str, value: object) -> None:
        with self._lock:
            self._store[key] = (time.time(), value)
