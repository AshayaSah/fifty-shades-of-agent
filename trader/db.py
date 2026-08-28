import os
from dotenv import load_dotenv
import psycopg

load_dotenv()

_conn = None


class DBError(Exception):
    """Raised when a database operation fails."""


def _get_conn() -> psycopg.Connection:
    global _conn
    url = os.getenv("DATABASE_URL")
    if not url:
        raise DBError(
            "Missing DATABASE_URL environment variable. Set it in .env."
        )
    if _conn is None or _conn.closed:
        _conn = psycopg.connect(url, autocommit=True, prepare_threshold=None)
    return _conn


def init_db() -> None:
    """Create the proposals table if it doesn't exist."""
    conn = _get_conn()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS proposals (
            id           TEXT PRIMARY KEY,
            symbol       TEXT NOT NULL,
            direction    TEXT NOT NULL,
            entry        DOUBLE PRECISION NOT NULL,
            sl           DOUBLE PRECISION NOT NULL,
            tp           DOUBLE PRECISION NOT NULL,
            rationale    TEXT NOT NULL,
            status       TEXT NOT NULL,
            created_at   TIMESTAMPTZ NOT NULL,
            result       JSONB
        )
        """
    )


def close_db() -> None:
    global _conn
    if _conn is not None:
        _conn.close()
        _conn = None
