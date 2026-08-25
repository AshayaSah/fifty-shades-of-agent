from datetime import datetime, timezone
from unittest.mock import patch

from news_scraper.sources import fetch_bbc, fetch_newsapi


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
    assert results[1]["source"] == "Bloomberg"


@patch("news_scraper.sources.requests.get")
@patch.dict("os.environ", {"NEWSAPI_KEY": "fake-key-123"})
def test_fetch_newsapi_empty_articles(mock_get):
    mock_resp = mock_get.return_value
    mock_resp.json.return_value = {"status": "ok", "articles": []}

    results = fetch_newsapi("XYZNONEXISTENT")

    assert results == []
