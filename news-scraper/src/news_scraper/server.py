from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager

from mcp.server.fastmcp import FastMCP

from news_scraper import db, extraction, sentiment, sources

_MAX_ARTICLES = 15


@asynccontextmanager
async def lifespan(app):
    db.init_db()
    yield


mcp = FastMCP("news-scraper", host="0.0.0.0", port=8000, lifespan=lifespan)


@mcp.tool()
def scrape_news(symbol: str, company_keyword: str, days: int = 30) -> dict:
    """Scrape recent news articles about a company from BBC and NewsAPI,
    analyze sentiment, extract entities and event types, and save to the
    database. Optionally scrapes full article text.

    Args:
        symbol: Stock ticker symbol (e.g. "AAPL").
        company_keyword: Company name or keyword to search for in news articles.
        days: How many days back to search (default 30).

    Returns:
        Summary with article counts, full text scrape count, and event breakdown.
    """
    with ThreadPoolExecutor(max_workers=2) as pool:
        bbc_f = pool.submit(sources.fetch_bbc, company_keyword)
        newsapi_f = pool.submit(sources.fetch_newsapi, company_keyword, days)
        bbc = bbc_f.result()
        newsapi = newsapi_f.result()

    all_articles = (bbc + newsapi)[:_MAX_ARTICLES]

    texts_for_sentiment = [a["text"] for a in all_articles]
    batch_scores = sentiment.score_texts(texts_for_sentiment)

    rows = []
    event_counts = {}
    for i, article in enumerate(all_articles):
        text_for_analysis = texts_for_sentiment[i]
        score = batch_scores[i]
        entities = extraction.extract_entities(text_for_analysis)
        event_type = extraction.classify_event(text_for_analysis)
        entity_scores = extraction.score_entities(text_for_analysis, entities)
        event_counts[event_type] = event_counts.get(event_type, 0) + 1
        rows.append((
            symbol,
            article["source"],
            article["title"],
            article["url"],
            article["published_at"],
            score,
            None,
            entities,
            event_type,
            entity_scores,
        ))

    db.save_articles(rows)

    return {
        "symbol": symbol,
        "articles_found": len(bbc + newsapi),
        "articles_saved": len(rows),
        "full_text_scraped": 0,
        "event_breakdown": event_counts,
    }


@mcp.tool()
def get_news(symbol: str, days: int = 30) -> list[dict]:
    """Retrieve previously scraped news articles for a stock symbol.

    Args:
        symbol: Stock ticker symbol (e.g. "AAPL").
        days: How many days back to retrieve (default 30).

    Returns:
        List of articles with source, title, URL, publication time,
        sentiment score, entities, event type, and full article text.
    """
    rows = db.fetch_articles(symbol, days)
    return [
        {
            "source": row[0],
            "title": row[1],
            "url": row[2],
            "published_at": row[3],
            "sentiment_score": row[4],
            "full_text": row[5],
            "entities": row[6],
            "event_type": row[7],
            "entity_scores": row[8],
        }
        for row in rows
    ]


@mcp.tool()
def get_sentiment_summary(symbol: str, days: int = 30) -> dict:
    """Get an aggregate sentiment summary for a stock symbol based on scraped news.

    Args:
        symbol: Stock ticker symbol (e.g. "AAPL").
        days: How many days back to analyze (default 30).

    Returns:
        Symbol, article count, average sentiment, event breakdown,
        and average per-entity sentiment across all articles.
    """
    rows = db.fetch_articles(symbol, days)
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


@mcp.tool()
def get_sentiment_trend(symbol: str, days: int = 30) -> list[dict]:
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
    rows = db.fetch_sentiment_trend(symbol, days)
    return [
        {"date": str(row[0]), "avg_sentiment": float(row[1]), "article_count": row[2]}
        for row in rows
    ]


@mcp.tool()
def get_source_comparison(symbol: str, days: int = 30) -> list[dict]:
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
    rows = db.fetch_source_comparison(symbol, days)
    return [
        {"source": row[0], "avg_sentiment": float(row[1]), "article_count": row[2]}
        for row in rows
    ]
