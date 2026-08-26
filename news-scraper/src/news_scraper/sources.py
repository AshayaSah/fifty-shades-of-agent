import os
from datetime import datetime, timedelta, timezone

import feedparser
import requests
import trafilatura
from dotenv import load_dotenv

load_dotenv()

BBC_RSS_URL = "http://feeds.bbci.co.uk/news/business/rss.xml"
NEWSAPI_BASE = "https://newsapi.org/v2/everything"
_SCRAPE_TIMEOUT = 8


def scrape_article_text(url: str) -> str | None:
    """Download and extract clean article body text from a URL.

    Returns None if extraction fails or the page is inaccessible.
    """
    try:
        downloaded = trafilatura.fetch_url(url)
        if downloaded:
            return trafilatura.extract(downloaded, include_comments=False, include_tables=False)
    except Exception:
        pass
    return None


def fetch_bbc(symbol_keyword: str) -> list[dict]:
    feed = feedparser.parse(BBC_RSS_URL)
    keyword_lower = symbol_keyword.lower()
    results = []
    for entry in feed.entries:
        title = entry.get("title", "")
        summary = entry.get("summary", "")
        published_parsed = entry.get("published_parsed")
        if keyword_lower in title.lower() or keyword_lower in summary.lower():
            published = datetime(*published_parsed[:6], tzinfo=timezone.utc) if published_parsed else None
            results.append({
                "source": "BBC",
                "title": title,
                "url": entry.get("link", ""),
                "published_at": published,
                "text": summary or title,
                "full_text": None,
            })
    return results


def fetch_newsapi(symbol_keyword: str, days: int = 30) -> list[dict]:
    api_key = os.environ.get("NEWSAPI_KEY", "")
    from_date = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
    params = {
        "qInTitle": symbol_keyword,
        "from": from_date,
        "sortBy": "publishedAt",
        "language": "en",
        "apiKey": api_key,
    }
    resp = requests.get(NEWSAPI_BASE, params=params)
    resp.raise_for_status()
    data = resp.json()
    results = []
    for article in data.get("articles", []):
        published = None
        if article.get("publishedAt"):
            published = datetime.fromisoformat(article["publishedAt"].replace("Z", "+00:00"))
        source_name = article.get("source", {}).get("name", "Unknown")
        results.append({
            "source": source_name,
            "title": article.get("title", ""),
            "url": article.get("url", ""),
            "published_at": published,
            "text": article.get("description") or article.get("title", ""),
            "full_text": None,
        })
    return results
