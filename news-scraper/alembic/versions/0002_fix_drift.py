"""Fix production drift: TIMESTAMPTZ columns + missing job_uuid + index.

Revision ID: 0002_fix_drift
Revises: 0001_initial
Create Date: 2026-08-29

History:
  The original 0001_initial migration was hand-written and used TIMESTAMP
  instead of TIMESTAMPTZ for `news_articles.published_at` and
  `news_articles.scraped_at`.  The old 0002 migration (job_uuid) had a
  broken revision chain and was never applied.  This migration brings the
  production database in line with the ORM models.
"""
from __future__ import annotations

from alembic import op

revision = "0002_fix_drift"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Fix TIMESTAMP → TIMESTAMPTZ on news_articles columns that were
    #    created without timezone in the original bootstrap.
    op.execute(
        "ALTER TABLE news_articles "
        "ALTER COLUMN published_at TYPE TIMESTAMPTZ "
        "USING published_at AT TIME ZONE 'UTC'"
    )
    op.execute(
        "ALTER TABLE news_articles "
        "ALTER COLUMN scraped_at TYPE TIMESTAMPTZ "
        "USING scraped_at AT TIME ZONE 'UTC'"
    )

    # 2. Add job_uuid to scrape_jobs (idempotent — only if missing).
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'scrape_jobs' AND column_name = 'job_uuid'
            ) THEN
                ALTER TABLE scrape_jobs ADD COLUMN job_uuid UUID
                    NOT NULL DEFAULT gen_random_uuid();
            END IF;
        END $$;
        """
    )

    # 3. Ensure UNIQUE constraint on job_uuid.
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'scrape_jobs_job_uuid_key'
            ) THEN
                ALTER TABLE scrape_jobs
                    ADD CONSTRAINT scrape_jobs_job_uuid_key UNIQUE (job_uuid);
            END IF;
        END $$;
        """
    )

    # 4. Ensure index on job_uuid.
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_scrape_jobs_job_uuid "
        "ON scrape_jobs (job_uuid)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_scrape_jobs_job_uuid")
    op.execute(
        "ALTER TABLE scrape_jobs DROP CONSTRAINT IF EXISTS scrape_jobs_job_uuid_key"
    )
    op.execute(
        "ALTER TABLE scrape_jobs DROP COLUMN IF EXISTS job_uuid"
    )
    op.execute(
        "ALTER TABLE news_articles "
        "ALTER COLUMN published_at TYPE TIMESTAMP "
        "USING published_at"
    )
    op.execute(
        "ALTER TABLE news_articles "
        "ALTER COLUMN scraped_at TYPE TIMESTAMP "
        "USING scraped_at"
    )
