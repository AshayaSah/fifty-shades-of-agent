import json
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
    full_text TEXT,
    sentiment_score FLOAT,
    scraped_at TIMESTAMP DEFAULT NOW()
);
"""

_MIGRATIONS = [
    "ALTER TABLE news_articles ADD COLUMN IF NOT EXISTS full_text TEXT;",
    "ALTER TABLE news_articles ADD COLUMN IF NOT EXISTS entities JSONB;",
    "ALTER TABLE news_articles ADD COLUMN IF NOT EXISTS event_type TEXT;",
    "ALTER TABLE news_articles ADD COLUMN IF NOT EXISTS entity_scores JSONB;",
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


def save_article(symbol, source, title, url, published_at, sentiment_score,
                 full_text=None, entities=None, event_type=None, entity_scores=None):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO news_articles
                    (symbol, source, title, url, published_at, sentiment_score,
                     full_text, entities, event_type, entity_scores)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (url) DO NOTHING
                """,
                (symbol, source, title, url, published_at, sentiment_score,
                 full_text, json.dumps(entities) if entities else None,
                 event_type, json.dumps(entity_scores) if entity_scores else None),
            )
        conn.commit()


def save_articles(articles):
    """Batch insert articles in a single connection/transaction.

    Each item in `articles` is a tuple:
    (symbol, source, title, url, published_at, sentiment_score,
     full_text, entities, event_type, entity_scores)
    """
    if not articles:
        return
    serialized = []
    for row in articles:
        serialized.append((
            row[0], row[1], row[2], row[3], row[4], row[5],
            row[6],
            json.dumps(row[7]) if row[7] else None,
            row[8],
            json.dumps(row[9]) if row[9] else None,
        ))
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.executemany(
                """
                INSERT INTO news_articles
                    (symbol, source, title, url, published_at, sentiment_score,
                     full_text, entities, event_type, entity_scores)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (url) DO NOTHING
                """,
                serialized,
            )
        conn.commit()


def fetch_articles(symbol, days=30):
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT source, title, url, published_at, sentiment_score,
                       full_text, entities, event_type, entity_scores
                FROM news_articles
                WHERE symbol = %s AND published_at >= %s
                ORDER BY published_at DESC
                """,
                (symbol, cutoff),
            )
            return cur.fetchall()


def fetch_sentiment_trend(symbol, days=30):
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT DATE(published_at) AS day,
                       ROUND(AVG(sentiment_score)::numeric, 4) AS avg_sentiment,
                       COUNT(*) AS article_count
                FROM news_articles
                WHERE symbol = %s AND published_at >= %s AND sentiment_score IS NOT NULL
                GROUP BY day
                ORDER BY day DESC
                """,
                (symbol, cutoff),
            )
            return cur.fetchall()


def fetch_source_comparison(symbol, days=30):
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT source,
                       ROUND(AVG(sentiment_score)::numeric, 4) AS avg_sentiment,
                       COUNT(*) AS article_count
                FROM news_articles
                WHERE symbol = %s AND published_at >= %s AND sentiment_score IS NOT NULL
                GROUP BY source
                ORDER BY avg_sentiment DESC
                """,
                (symbol, cutoff),
            )
            return cur.fetchall()
