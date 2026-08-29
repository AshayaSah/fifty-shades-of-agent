import os
from datetime import datetime, timedelta, timezone

import psycopg  # noqa: F401  (registers the psycopg dialect with SQLAlchemy)
from dotenv import load_dotenv
from sqlalchemy import Numeric, func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from news_scraper.models import Base, NewsArticle, ScrapeJob

load_dotenv()

_engine: AsyncEngine | None = None


def _db_url() -> str:
    url = os.environ["DATABASE_URL"]
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg://", 1)
    return url


def get_async_engine() -> AsyncEngine:
    """Return a pooled async engine, created once per process."""
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            _db_url(),
            pool_pre_ping=True,
            pool_recycle=300,
            pool_size=5,
            max_overflow=10,
        )
    return _engine


async def init_db(engine: AsyncEngine | None = None):
    """Create schema if missing. Alembic owns migrations; this keeps the app
    bootable in fresh environments (tests, dev) where migrations haven't run."""
    engine = engine or get_async_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def save_article(
    engine: AsyncEngine | None = None,
    *,
    symbol,
    source,
    title,
    url,
    published_at,
    sentiment_score,
    full_text=None,
    entities=None,
    event_type=None,
    entity_scores=None,
):
    stmt = (
        insert(NewsArticle)
        .values(
            symbol=symbol,
            source=source,
            title=title,
            url=url,
            published_at=published_at,
            sentiment_score=sentiment_score,
            full_text=full_text,
            entities=entities,
            event_type=event_type,
            entity_scores=entity_scores,
        )
        .on_conflict_do_nothing(index_elements=[NewsArticle.url])
    )
    engine = engine or get_async_engine()
    async with engine.begin() as conn:
        await conn.execute(stmt)


async def save_articles(engine: AsyncEngine | None = None, *, articles):
    """Batch insert articles in a single async statement/transaction.

    Each item in `articles` is a tuple:
    (symbol, source, title, url, published_at, sentiment_score,
     full_text, entities, event_type, entity_scores)
    """
    if not articles:
        return
    rows = [
        {
            "symbol": r[0],
            "source": r[1],
            "title": r[2],
            "url": r[3],
            "published_at": r[4],
            "sentiment_score": r[5],
            "full_text": r[6],
            "entities": r[7],
            "event_type": r[8],
            "entity_scores": r[9],
        }
        for r in articles
    ]
    engine = engine or get_async_engine()
    stmt = insert(NewsArticle).on_conflict_do_nothing(index_elements=[NewsArticle.url])
    async with engine.begin() as conn:
        await conn.execute(stmt, rows)


async def fetch_articles(engine: AsyncEngine | None = None, *, symbol, days=30):
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    stmt = (
        select(
            NewsArticle.source,
            NewsArticle.title,
            NewsArticle.url,
            NewsArticle.published_at,
            NewsArticle.sentiment_score,
            NewsArticle.full_text,
            NewsArticle.entities,
            NewsArticle.event_type,
            NewsArticle.entity_scores,
        )
        .where(
            NewsArticle.symbol == symbol,
            NewsArticle.published_at >= cutoff,
        )
        .order_by(NewsArticle.published_at.desc())
    )
    engine = engine or get_async_engine()
    async with engine.begin() as conn:
        result = await conn.execute(stmt)
        return result.fetchall()


async def fetch_sentiment_trend(engine: AsyncEngine | None = None, *, symbol, days=30):
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    day = func.date(NewsArticle.published_at).label("day")
    avg_sentiment = func.round(
        func.cast(func.avg(NewsArticle.sentiment_score), Numeric), 4
    ).label("avg_sentiment")
    stmt = (
        select(
            day,
            avg_sentiment,
            func.count().label("article_count"),
        )
        .where(
            NewsArticle.symbol == symbol,
            NewsArticle.published_at >= cutoff,
            NewsArticle.sentiment_score.is_not(None),
        )
        .group_by(day)
        .order_by(day.desc())
    )
    engine = engine or get_async_engine()
    async with engine.begin() as conn:
        result = await conn.execute(stmt)
        return result.fetchall()


async def fetch_source_comparison(
    engine: AsyncEngine | None = None, *, symbol, days=30
):
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    stmt = (
        select(
            NewsArticle.source,
            func.round(
                func.cast(func.avg(NewsArticle.sentiment_score), Numeric), 4
            ).label("avg_sentiment"),
            func.count().label("article_count"),
        )
        .where(
            NewsArticle.symbol == symbol,
            NewsArticle.published_at >= cutoff,
            NewsArticle.sentiment_score.is_not(None),
        )
        .group_by(NewsArticle.source)
        .order_by(func.avg(NewsArticle.sentiment_score).desc())
    )
    engine = engine or get_async_engine()
    async with engine.begin() as conn:
        result = await conn.execute(stmt)
        return result.fetchall()


async def create_job(
    engine: AsyncEngine | None = None, *, symbol, company_keyword, days
):
    stmt = (
        insert(ScrapeJob)
        .values(
            symbol=symbol,
            company_keyword=company_keyword,
            days=days,
            status="pending",
        )
        .returning(ScrapeJob.id)
    )
    engine = engine or get_async_engine()
    async with engine.begin() as conn:
        result = await conn.execute(stmt)
        return result.scalar_one()


async def set_job_status(
    engine: AsyncEngine | None = None,
    *,
    job_id,
    status,
    result=None,
    error=None,
    started_at=None,
    finished_at=None,
):
    values = {"status": status}
    if result is not None:
        values["result"] = result
    if error is not None:
        values["error"] = error
    if started_at is not None:
        values["started_at"] = started_at
    if finished_at is not None:
        values["finished_at"] = finished_at
    stmt = update(ScrapeJob).where(ScrapeJob.id == job_id).values(**values)
    engine = engine or get_async_engine()
    async with engine.begin() as conn:
        await conn.execute(stmt)


async def get_job(engine: AsyncEngine | None = None, *, job_id):
    stmt = select(
        ScrapeJob.id,
        ScrapeJob.job_uuid,
        ScrapeJob.symbol,
        ScrapeJob.company_keyword,
        ScrapeJob.days,
        ScrapeJob.status,
        ScrapeJob.result,
        ScrapeJob.error,
    ).where(ScrapeJob.id == job_id)
    engine = engine or get_async_engine()
    async with engine.begin() as conn:
        result = await conn.execute(stmt)
        return result.one_or_none()


async def recover_stale_jobs(engine: AsyncEngine | None = None):
    """Mark jobs stuck in 'running' (e.g. after a worker restart) as failed.

    Called on startup: a job mid-flight when the worker died would otherwise
    stay 'running' forever, since the queue re-processes only 'pending' jobs.
    """
    engine = engine or get_async_engine()
    async with engine.begin() as conn:
        result = await conn.execute(
            update(ScrapeJob)
            .where(ScrapeJob.status == "running")
            .values(status="failed", error="worker restart; job abandoned")
        )
    return result.rowcount or 0
