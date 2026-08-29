import asyncio
from contextlib import asynccontextmanager

from fastmcp import FastMCP

from news_scraper import db, jobs, sentiment
from news_scraper.jobs import queue_logger


@asynccontextmanager
async def lifespan(server):
    await db.init_db()
    recovered = await db.recover_stale_jobs()
    if recovered:
        queue_logger.warning("recovered %s stale 'running' job(s) after restart", recovered)
    await asyncio.to_thread(sentiment.warm_start)
    jobs.queue.start()
    try:
        yield
    finally:
        jobs.queue.stop()


mcp = FastMCP("news-scraper", lifespan=lifespan)


@mcp.tool
async def scrape_news(symbol: str, company_keyword: str, days: int = 30) -> dict:
    """Queue a news scrape job for a company (BBC + NewsAPI), analyze
    sentiment/entities/events, and save to the database.

    This tool returns immediately with a job_id. Poll `get_job_status` for
    the result. Scrapes run in the background so they never block the server
    or time out the request.

    Args:
        symbol: Stock ticker symbol (e.g. "AAPL").
        company_keyword: Company name or keyword to search for in news articles.
        days: How many days back to search (default 30).

    Returns:
        Job id and initial status ("pending").
    """
    symbol = symbol.strip()
    company_keyword = company_keyword.strip()
    job_id = await db.create_job(
        symbol=symbol, company_keyword=company_keyword, days=days
    )
    job = await db.get_job(job_id=job_id)
    job_uuid = str(job.job_uuid) if job else None
    if not jobs.queue.enqueue(job_id, job_uuid=job_uuid):
        error = "queue is full, try again later"
        await db.set_job_status(job_id=job_id, status="failed", error=error)
        return {"job_id": job_id, "job_uuid": job_uuid, "status": "failed", "error": error}
    return {"job_id": job_id, "job_uuid": job_uuid, "status": "pending"}


@mcp.tool
async def get_job_status(job_id: int) -> dict:
    """Check the status of a queued scrape job.

    Args:
        job_id: Job id returned by `scrape_news`.

    Returns:
        Status ("pending", "running", "completed", "failed"), the scrape
        result summary once completed, or the error message on failure.
    """
    job = await db.get_job(job_id=job_id)
    if job is None:
        return {"job_id": job_id, "status": "not_found"}
    return {
        "job_id": job.id,
        "job_uuid": str(job.job_uuid) if job.job_uuid else None,
        "symbol": job.symbol,
        "company_keyword": job.company_keyword,
        "status": job.status,
        "result": job.result,
        "error": job.error,
    }


@mcp.tool
async def get_news(symbol: str, days: int = 30) -> list[dict]:
    """Retrieve previously scraped news articles for a stock symbol.

    Args:
        symbol: Stock ticker symbol (e.g. "AAPL").
        days: How many days back to retrieve (default 30).

    Returns:
        List of articles with source, title, URL, publication time,
        sentiment score, entities, event type, and full article text.
    """
    symbol = symbol.strip()
    rows = await db.fetch_articles(symbol=symbol, days=days)
    return [
        {
            "source": row[0],
            "title": row[1],
            "url": row[2],
            "published_at": str(row[3]) if row[3] else None,
            "sentiment_score": row[4],
            "full_text": row[5],
            "entities": row[6],
            "event_type": row[7],
            "entity_scores": row[8],
        }
        for row in rows
    ]


@mcp.tool
async def get_sentiment_summary(symbol: str, days: int = 30) -> dict:
    """Get an aggregate sentiment summary for a stock symbol based on scraped news.

    Args:
        symbol: Stock ticker symbol (e.g. "AAPL").
        days: How many days back to analyze (default 30).

    Returns:
        Symbol, article count, average sentiment, event breakdown,
        and average per-entity sentiment across all articles.
    """
    symbol = symbol.strip()
    rows = await db.fetch_articles(symbol=symbol, days=days)
    scores = [row[4] for row in rows if row[4] is not None]
    avg = sum(scores) / len(scores) if scores else None
    event_counts = {}
    for row in rows:
        et = row[7]
        if et:
            event_counts[et] = event_counts.get(et, 0) + 1

    entity_agg: dict[str, list[float]] = {}
    for row in rows:
        es = row[8]
        if es:
            for name, val in es.items():
                entity_agg.setdefault(name, []).append(val)
    avg_entity_scores = {
        name: round(sum(vals) / len(vals), 4)
        for name, vals in entity_agg.items()
    }

    return {
        "symbol": symbol,
        "article_count": len(rows),
        "average_sentiment": avg,
        "event_breakdown": event_counts,
        "avg_entity_sentiment": avg_entity_scores,
    }


@mcp.tool
async def get_sentiment_trend(symbol: str, days: int = 30) -> list[dict]:
    """Get daily sentiment trend for a stock symbol over time.

    Shows how average sentiment changes day-by-day, useful for
    spotting momentum shifts or reaction to events.

    Args:
        symbol: Stock ticker symbol (e.g. "AAPL").
        days: How many days back to analyze (default 30).

    Returns:
        List of daily entries with date, average sentiment, and article count,
        most recent first.
    """
    symbol = symbol.strip()
    rows = await db.fetch_sentiment_trend(symbol=symbol, days=days)
    return [
        {"date": str(row[0]), "avg_sentiment": float(row[1]), "article_count": row[2]}
        for row in rows
    ]


@mcp.tool
async def get_source_comparison(symbol: str, days: int = 30) -> list[dict]:
    """Compare sentiment across different news sources for a stock symbol.

    Shows which outlets are more positive or negative about a company,
    useful for understanding media bias or coverage differences.

    Args:
        symbol: Stock ticker symbol (e.g. "AAPL").
        days: How many days back to analyze (default 30).

    Returns:
        List of source entries with source name, average sentiment,
        and article count, most positive first.
    """
    symbol = symbol.strip()
    rows = await db.fetch_source_comparison(symbol=symbol, days=days)
    return [
        {"source": row[0], "avg_sentiment": float(row[1]), "article_count": row[2]}
        for row in rows
    ]