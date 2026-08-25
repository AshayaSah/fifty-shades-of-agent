from mcp.server.fastmcp import FastMCP

from news_scraper import db, sentiment, sources

mcp = FastMCP("news-scraper")

db.init_db()


@mcp.tool()
def scrape_news(symbol: str, company_keyword: str, days: int = 30) -> dict:
    """Scrape recent news articles about a company from BBC and NewsAPI,
    score their sentiment, and save them to the database.

    Args:
        symbol: Stock ticker symbol (e.g. "AAPL").
        company_keyword: Company name or keyword to search for in news articles.
        days: How many days back to search (default 30).

    Returns:
        Summary with article counts found and saved.
    """
    bbc = sources.fetch_bbc(company_keyword)
    newsapi = sources.fetch_newsapi(company_keyword, days)
    all_articles = bbc + newsapi

    saved = 0
    for article in all_articles:
        score = sentiment.score_text(article["text"])
        db.save_article(
            symbol=symbol,
            source=article["source"],
            title=article["title"],
            url=article["url"],
            published_at=article["published_at"],
            sentiment_score=score,
        )
        saved += 1

    return {"symbol": symbol, "articles_found": len(all_articles), "articles_saved": saved}


@mcp.tool()
def get_news(symbol: str, days: int = 30) -> list[dict]:
    """Retrieve previously scraped news articles for a stock symbol.

    Args:
        symbol: Stock ticker symbol (e.g. "AAPL").
        days: How many days back to retrieve (default 30).

    Returns:
        List of articles with source, title, URL, publication time, and sentiment score.
    """
    rows = db.fetch_articles(symbol, days)
    return [
        {
            "source": row[0],
            "title": row[1],
            "url": row[2],
            "published_at": row[3],
            "sentiment_score": row[4],
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


if __name__ == "__main__":
    mcp.run(transport="stdio")
