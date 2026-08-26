from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager

from mcp.server.fastmcp import FastMCP

from news_scraper import db, sentiment, sources


@asynccontextmanager
async def lifespan(app):
    db.init_db()
    yield


mcp = FastMCP("news-scraper", host="0.0.0.0", port=8000, lifespan=lifespan)


@mcp.tool()
def scrape_news(symbol: str, company_keyword: str, days: int = 30) -> dict:
    """Scrape recent news articles about a company from BBC and NewsAPI,
    extract full article text, score sentiment, and save to the database.

    Args:
        symbol: Stock ticker symbol (e.g. "AAPL").
        company_keyword: Company name or keyword to search for in news articles.
        days: How many days back to search (default 30).

    Returns:
        Summary with article counts found and saved.
    """
    with ThreadPoolExecutor(max_workers=2) as pool:
        bbc_f = pool.submit(sources.fetch_bbc, company_keyword)
        newsapi_f = pool.submit(sources.fetch_newsapi, company_keyword, days)
        bbc = bbc_f.result()
        newsapi = newsapi_f.result()

    all_articles = bbc + newsapi

    urls = [a["url"] for a in all_articles if a["url"]]
    with ThreadPoolExecutor(max_workers=4) as pool:
        full_texts = list(pool.map(sources.scrape_article_text, urls))

    for article, full_text in zip(all_articles, full_texts):
        article["full_text"] = full_text

    rows = []
    for article in all_articles:
        text_for_sentiment = article["full_text"] or article["text"]
        score = sentiment.score_text(text_for_sentiment)
        rows.append((
            symbol,
            article["source"],
            article["title"],
            article["url"],
            article["published_at"],
            score,
            article["full_text"],
        ))

    db.save_articles(rows)

    scraped = sum(1 for ft in full_texts if ft)
    return {
        "symbol": symbol,
        "articles_found": len(all_articles),
        "articles_saved": len(rows),
        "full_text_scraped": scraped,
    }


@mcp.tool()
def get_news(symbol: str, days: int = 30) -> list[dict]:
    """Retrieve previously scraped news articles for a stock symbol.

    Args:
        symbol: Stock ticker symbol (e.g. "AAPL").
        days: How many days back to retrieve (default 30).

    Returns:
        List of articles with source, title, URL, publication time,
        sentiment score, and full article text (if available).
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
        Symbol, total article count, and average sentiment score (range -1.0 to 1.0).
    """
    rows = db.fetch_articles(symbol, days)
    scores = [row[4] for row in rows if row[4] is not None]
    avg = sum(scores) / len(scores) if scores else None
    return {"symbol": symbol, "article_count": len(rows), "average_sentiment": avg}
