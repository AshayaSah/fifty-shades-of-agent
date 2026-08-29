"""Initial schema: news_articles + scrape_jobs.

Revision ID: 0001_initial
Revises:
Create Date: 2026-08-29

History:
  - `news_articles` already existed in production (created by the pre-Alembic
    bootstrap), so the DDL below is idempotent — it works both on a fresh
    database and against the existing schema with no-op behavior.
  - `scrape_jobs.job_uuid` is included here with UNIQUE + INDEX from the
    start, replacing the earlier incremental 0002 migration which had a
    broken revision chain and was missing the unique constraint.
"""
from __future__ import annotations

from alembic import op

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS news_articles (
            id SERIAL PRIMARY KEY,
            symbol TEXT NOT NULL,
            source TEXT NOT NULL,
            title TEXT NOT NULL,
            url TEXT NOT NULL UNIQUE,
            published_at TIMESTAMPTZ,
            full_text TEXT,
            sentiment_score DOUBLE PRECISION,
            entities JSONB,
            event_type TEXT,
            entity_scores JSONB,
            scraped_at TIMESTAMPTZ DEFAULT now()
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_news_articles_symbol "
        "ON news_articles (symbol)"
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS scrape_jobs (
            id SERIAL PRIMARY KEY,
            job_uuid UUID NOT NULL DEFAULT gen_random_uuid() UNIQUE,
            symbol TEXT NOT NULL,
            company_keyword TEXT NOT NULL,
            days INTEGER NOT NULL DEFAULT 30,
            status TEXT NOT NULL DEFAULT 'pending',
            result JSONB,
            error TEXT,
            created_at TIMESTAMPTZ DEFAULT now(),
            started_at TIMESTAMPTZ,
            finished_at TIMESTAMPTZ
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_scrape_jobs_job_uuid "
        "ON scrape_jobs (job_uuid)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS scrape_jobs")
    op.execute("DROP TABLE IF EXISTS news_articles")
