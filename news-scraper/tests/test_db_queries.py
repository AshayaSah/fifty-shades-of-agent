from datetime import date
from unittest.mock import MagicMock, patch

from news_scraper.db import fetch_sentiment_trend, fetch_source_comparison


@patch("news_scraper.db.get_conn")
def test_fetch_sentiment_trend(mock_get_conn):
    mock_conn = MagicMock()
    mock_get_conn.return_value.__enter__.return_value = mock_conn
    mock_conn.cursor.return_value.__enter__.return_value.fetchall.return_value = [
        (date(2026, 8, 25), 0.65, 3),
        (date(2026, 8, 24), -0.12, 2),
        (date(2026, 8, 23), 0.30, 1),
    ]

    result = fetch_sentiment_trend("AAPL", days=30)

    assert len(result) == 3
    assert result[0][0] == date(2026, 8, 25)
    assert float(result[0][1]) == 0.65
    assert result[0][2] == 3
    assert float(result[1][1]) == -0.12


@patch("news_scraper.db.get_conn")
def test_fetch_sentiment_trend_empty(mock_get_conn):
    mock_conn = MagicMock()
    mock_get_conn.return_value.__enter__.return_value = mock_conn
    mock_conn.cursor.return_value.__enter__.return_value.fetchall.return_value = []

    result = fetch_sentiment_trend("XYZ", days=30)
    assert result == []


@patch("news_scraper.db.get_conn")
def test_fetch_source_comparison(mock_get_conn):
    mock_conn = MagicMock()
    mock_get_conn.return_value.__enter__.return_value = mock_conn
    mock_conn.cursor.return_value.__enter__.return_value.fetchall.return_value = [
        ("Reuters", 0.72, 5),
        ("BBC", 0.35, 3),
        ("Bloomberg", -0.10, 2),
    ]

    result = fetch_source_comparison("AAPL", days=30)

    assert len(result) == 3
    assert result[0][0] == "Reuters"
    assert float(result[0][1]) == 0.72
    assert result[0][2] == 5
    assert result[2][0] == "Bloomberg"


@patch("news_scraper.db.get_conn")
def test_fetch_source_comparison_empty(mock_get_conn):
    mock_conn = MagicMock()
    mock_get_conn.return_value.__enter__.return_value = mock_conn
    mock_conn.cursor.return_value.__enter__.return_value.fetchall.return_value = []

    result = fetch_source_comparison("XYZ", days=30)
    assert result == []
