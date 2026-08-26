import os
from datetime import datetime, timedelta, timezone

import psycopg
from dotenv import load_dotenv

load_dotenv()

_DDL = """
CREATE TABLE IF NOT EXISTS news_articles (
    id SERIAL PRIMARY KEY,
    symbol TEXT NOT NULL,
    source TEXT NOT NULL,
    title TEXT NOT NULL,
    url TEXT UNIQUE NOT NULL,
    published_at TIMESTAMP,
    sentiment_score FLOAT,
    scraped_at TIMESTAMP DEFAULT NOW()
);
"""

_MIGRATIONS = [
    "ALTER TABLE news_articles ADD COLUMN IF NOT EXISTS full_text TEXT;",
]


def get_conn():
    return psycopg.connect(os.environ["DATABASE_URL"], connect_timeout=10)


def init_db():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(_DDL)
            for migration in _MIGRATIONS:
                cur.execute(migration)
        conn.commit()


def save_article(symbol, source, title, url, published_at, sentiment_score, full_text=None):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO news_articles (symbol, source, title, url, published_at, sentiment_score, full_text)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (url) DO NOTHING
                """,
                (symbol, source, title, url, published_at, sentiment_score, full_text),
            )
        conn.commit()


def save_articles(articles):
    """Batch insert articles in a single connection/transaction.

    Each item in `articles` is a tuple:
    (symbol, source, title, url, published_at, sentiment_score, full_text)
    """
    if not articles:
        return
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.executemany(
                """
                INSERT INTO news_articles (symbol, source, title, url, published_at, sentiment_score, full_text)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (url) DO NOTHING
                """,
                articles,
            )
        conn.commit()


def fetch_articles(symbol, days=30):
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT source, title, url, published_at, sentiment_score, full_text
                FROM news_articles
                WHERE symbol = %s AND published_at >= %s
                ORDER BY published_at DESC
                """,
                (symbol, cutoff),
            )
            return cur.fetchall()
