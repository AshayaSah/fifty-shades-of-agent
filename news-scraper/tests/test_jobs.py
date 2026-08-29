import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from news_scraper import jobs
from news_scraper.jobs import JobQueue, execute_scrape


@pytest.fixture(autouse=True)
def _no_queue_autostart():
    yield


def _run(coro):
    return asyncio.run(coro)


class _FakeRow:
    def __init__(self, symbol="AAPL", company_keyword="Apple", days=7):
        self.symbol = symbol
        self.company_keyword = company_keyword
        self.days = days


def test_execute_scrape_batches_and_saves():
    bbc_articles = [
        {
            "source": "BBC", "title": "T1", "url": "u1",
            "published_at": "2026-08-01T00:00:00Z", "text": "Apple launches a phone.",
        }
    ]
    newsapi_articles = [
        {
            "source": "NewsAPI", "title": "T2", "url": "u2",
            "published_at": "2026-08-02T00:00:00Z", "text": "Apple stock rises.",
        }
    ]
    with (
        patch("news_scraper.jobs.sources.fetch_bbc", return_value=bbc_articles) as m_bbc,
        patch("news_scraper.jobs.sources.fetch_newsapi", return_value=newsapi_articles) as m_newsapi,
        patch("news_scraper.jobs.sentiment.score_texts", return_value={0: 0.5, 1: -0.2}) as m_score,
        patch(
            "news_scraper.jobs.extraction.analyze_article",
            side_effect=[({"orgs": ["Apple"]}, "product_launch", {"Apple": 0.5}),
                         ({"orgs": ["Apple"]}, "market_movement", {"Apple": -0.2})],
        ) as m_analyze,
        patch("news_scraper.jobs.db.save_articles", new=AsyncMock()) as m_save,
    ):
        result = _run(execute_scrape("AAPL", "Apple", 7))

    m_bbc.assert_called_once_with("Apple")
    m_newsapi.assert_called_once_with("Apple", 7)
    m_score.assert_called_once()
    assert m_analyze.call_count == 2
    assert result == {
        "symbol": "AAPL",
        "articles_found": 2,
        "articles_saved": 2,
        "full_text_scraped": 0,
        "event_breakdown": {"product_launch": 1, "market_movement": 1},
    }
    m_save.assert_awaited()
    saved = m_save.await_args.kwargs["articles"]
    assert len(saved) == 2
    assert saved[0][7] == {"orgs": ["Apple"]}


def test_job_queue_processes_until_completed():
    async def run():
        q = JobQueue()
        m_get_job = AsyncMock(return_value=_FakeRow())
        m_set_status = AsyncMock()
        expected = {"articles_saved": 3}
        m_execute = AsyncMock(return_value=expected)
        q.start()
        try:
            with (
                patch.object(jobs.db, "get_job", m_get_job),
                patch.object(jobs.db, "set_job_status", m_set_status),
                patch.object(jobs, "execute_scrape", m_execute),
            ):
                assert q.enqueue(1)
                deadline = time.monotonic() + 5
                while time.monotonic() < deadline:
                    done = [
                        c.kwargs.get("status") == "completed"
                        for c in m_set_status.await_args_list
                    ]
                    if any(done):
                        break
                    await asyncio.sleep(0.02)
        finally:
            q.stop()

        assert any(
            c.kwargs.get("status") == "completed" for c in m_set_status.await_args_list
        )
        completed_call = [
            c for c in m_set_status.await_args_list
            if c.kwargs.get("status") == "completed"
        ][0]
        assert completed_call.kwargs["result"] == expected

    _run(run())


def test_job_queue_survives_idle_timeout():
    """The worker must keep running through an idle `queue.Empty` window."""
    async def run():
        q = JobQueue()
        m_get_job = AsyncMock(return_value=_FakeRow())
        m_set_status = AsyncMock()
        m_execute = AsyncMock(return_value={"articles_saved": 1})
        q.start()
        try:
            with (
                patch.object(jobs.db, "get_job", m_get_job),
                patch.object(jobs.db, "set_job_status", m_set_status),
                patch.object(jobs, "execute_scrape", m_execute),
            ):
                await asyncio.sleep(0.8)
                assert q.enqueue(1)
                deadline = time.monotonic() + 5
                while time.monotonic() < deadline:
                    if any(
                        c.kwargs.get("status") == "completed"
                        for c in m_set_status.await_args_list
                    ):
                        break
                    await asyncio.sleep(0.02)
        finally:
            q.stop()

        assert any(
            c.kwargs.get("status") == "completed"
            for c in m_set_status.await_args_list
        )

    _run(run())


def test_job_queue_marks_failed_on_exception():
    async def run():
        q = JobQueue()
        m_get_job = AsyncMock(return_value=_FakeRow())
        m_set_status = AsyncMock()
        async def boom(*args, **kwargs):
            raise RuntimeError("NewsAPI down")
        m_execute = boom
        q.start()
        try:
            with (
                patch.object(jobs.db, "get_job", m_get_job),
                patch.object(jobs.db, "set_job_status", m_set_status),
                patch.object(jobs, "execute_scrape", m_execute),
            ):
                assert q.enqueue(1)
                deadline = time.monotonic() + 5
                while time.monotonic() < deadline:
                    failed = [
                        c.kwargs.get("status") == "failed"
                        for c in m_set_status.await_args_list
                    ]
                    if any(failed):
                        break
                    await asyncio.sleep(0.02)
        finally:
            q.stop()

        failed_call = [
            c for c in m_set_status.await_args_list
            if c.kwargs.get("status") == "failed"
        ][0]
        assert failed_call.kwargs["error"] == "NewsAPI down"

    _run(run())