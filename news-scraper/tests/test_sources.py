from datetime import datetime, timezone
from unittest.mock import patch

from news_scraper.sources import fetch_bbc, fetch_newsapi, scrape_article_text


@patch("news_scraper.sources.feedparser.parse")
def test_fetch_bbc_filters_by_keyword(mock_parse):
    ts = (2026, 8, 20, 10, 0, 0, 0, 0, 0)
    mock_parse.return_value.entries = [
        {
            "title": "Apple posts record revenue",
            "summary": "Apple Inc reported stellar quarterly results.",
            "link": "http://bbc.co.uk/1",
            "published_parsed": ts,
        },
        {
            "title": "Tesla stock dips",
            "summary": "Tesla shares fell after weak delivery numbers.",
            "link": "http://bbc.co.uk/2",
            "published_parsed": ts,
        },
    ]

    results = fetch_bbc("Apple")

    mock_parse.assert_called_once_with("http://feeds.bbci.co.uk/news/business/rss.xml")
    assert len(results) == 1
    assert results[0]["source"] == "BBC"
    assert results[0]["title"] == "Apple posts record revenue"
    assert results[0]["url"] == "http://bbc.co.uk/1"
    assert results[0]["published_at"] == datetime(2026, 8, 20, 10, 0, 0, tzinfo=timezone.utc)
    assert results[0]["text"] == "Apple Inc reported stellar quarterly results."
    assert results[0]["full_text"] is None


@patch("news_scraper.sources.requests.get")
@patch.dict("os.environ", {"NEWSAPI_KEY": "fake-key-123"})
def test_fetch_newsapi_parses_articles(mock_get):
    mock_resp = mock_get.return_value
    mock_resp.json.return_value = {
        "status": "ok",
        "articles": [
            {
                "source": {"name": "Reuters"},
                "title": "Apple launches new product",
                "url": "https://reuters.com/1",
                "publishedAt": "2026-08-15T08:30:00Z",
                "description": "Apple unveiled its latest device.",
            },
            {
                "source": {"name": "Bloomberg"},
                "title": "Markets rally on Apple news",
                "url": "https://bloomberg.com/2",
                "publishedAt": "2026-08-15T09:00:00Z",
                "description": "Tech stocks surged after Apple's announcement.",
            },
        ],
    }

    results = fetch_newsapi("Apple", days=7)

    assert len(results) == 2
    assert results[0]["source"] == "Reuters"
    assert results[0]["title"] == "Apple launches new product"
    assert results[0]["url"] == "https://reuters.com/1"
    assert results[0]["published_at"] == datetime(2026, 8, 15, 8, 30, 0, tzinfo=timezone.utc)
    assert results[0]["text"] == "Apple unveiled its latest device."
    assert results[0]["full_text"] is None
    assert results[1]["source"] == "Bloomberg"


@patch("news_scraper.sources.requests.get")
@patch.dict("os.environ", {"NEWSAPI_KEY": "fake-key-123"})
def test_fetch_newsapi_empty_articles(mock_get):
    mock_resp = mock_get.return_value
    mock_resp.json.return_value = {"status": "ok", "articles": []}

    results = fetch_newsapi("XYZNONEXISTENT")

    assert results == []


@patch("news_scraper.sources.trafilatura.fetch_url")
@patch("news_scraper.sources.trafilatura.extract")
def test_scrape_article_text_success(mock_extract, mock_fetch):
    mock_fetch.return_value = "<html><p>Full article body text here.</p></html>"
    mock_extract.return_value = "Full article body text here."

    result = scrape_article_text("http://example.com/article")

    assert result == "Full article body text here."
    mock_fetch.assert_called_once_with("http://example.com/article")


@patch("news_scraper.sources.trafilatura.fetch_url", side_effect=Exception("network error"))
def test_scrape_article_text_failure(mock_fetch):
    result = scrape_article_text("http://example.com/broken")
    assert result is None
