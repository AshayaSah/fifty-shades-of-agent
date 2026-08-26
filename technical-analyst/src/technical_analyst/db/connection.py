from contextlib import contextmanager

import psycopg
from psycopg_pool import ConnectionPool

from technical_analyst.config import settings

_pool: ConnectionPool | None = None


def get_pool() -> ConnectionPool:
    global _pool
    if _pool is None:
        if not settings.neon_database_url:
            raise RuntimeError("NEON_DATABASE_URL is not configured")
        _pool = ConnectionPool(settings.neon_database_url, min_size=1, max_size=5, open=True)
    return _pool


@contextmanager
def get_connection():
    pool = get_pool()
    with pool.connection() as conn:
        yield conn
