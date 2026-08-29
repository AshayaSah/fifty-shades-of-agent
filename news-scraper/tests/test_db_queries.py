import asyncio
from datetime import datetime, timedelta, timezone

from news_scraper.db import (
    create_job,
    fetch_articles,
    fetch_sentiment_trend,
    fetch_source_comparison,
    get_job,
    save_articles,
    set_job_status,
)

_DAY = timedelta(days=1)


def _now():
    return datetime.now(timezone.utc)


def _article(symbol, source, title, url, day_back, score, event=None):
    return (
        symbol, source, title, url, _now() - day_back * _DAY, score,
        None, None, event, None,
    )


def _run(coro):
    return asyncio.run(coro)


def test_fetch_articles_orders_desc_and_filters(pg_engine):
    async def scenario():
        await save_articles(
            engine=pg_engine,
            articles=[
                _article("AAPL", "BBC", "Apple old", "u1", 5, 0.1, "product_launch"),
                _article("AAPL", "Reuters", "Apple new", "u2", 0, 0.9, "earnings"),
                _article("MSFT", "BBC", "Other", "u3", 0, 0.5, "other"),
            ],
        )
        return await fetch_articles(engine=pg_engine, symbol="AAPL", days=30)

    rows = _run(scenario())

    assert [r[1] for r in rows] == ["Apple new", "Apple old"]
    assert float(rows[0][4]) == 0.9
    assert rows[0][7] == "earnings"


def test_fetch_articles_empty(pg_engine):
    assert _run(fetch_articles(engine=pg_engine, symbol="XYZ", days=30)) == []


def test_fetch_sentiment_trend(pg_engine):
    async def scenario():
        await save_articles(
            engine=pg_engine,
            articles=[
                _article("AAPL", "BBC", "a", "u1", 2, 0.5),
                _article("AAPL", "BBC", "b", "u2", 2, 0.1),
                _article("AAPL", "BBC", "c", "u3", 1, -0.2),
            ],
        )
        return await fetch_sentiment_trend(engine=pg_engine, symbol="AAPL", days=30)

    rows = _run(scenario())

    assert len(rows) == 2
    day_recent, day_older = rows[0], rows[1]
    assert day_recent[2] == 1
    assert day_older[2] == 2
    assert abs(float(day_older[1]) - 0.3) < 1e-6


def test_fetch_sentiment_trend_empty(pg_engine):
    assert _run(fetch_sentiment_trend(engine=pg_engine, symbol="XYZ", days=30)) == []


def test_fetch_source_comparison(pg_engine):
    async def scenario():
        await save_articles(
            engine=pg_engine,
            articles=[
                _article("AAPL", "Reuters", "a", "u1", 1, 0.9),
                _article("AAPL", "BBC", "b", "u2", 1, 0.3),
            ],
        )
        return await fetch_source_comparison(engine=pg_engine, symbol="AAPL", days=30)

    rows = _run(scenario())

    assert [r[0] for r in rows] == ["Reuters", "BBC"]
    assert float(rows[0][1]) == 0.9


def test_fetch_source_comparison_empty(pg_engine):
    assert (
        _run(fetch_source_comparison(engine=pg_engine, symbol="XYZ", days=30)) == []
    )


def test_job_lifecycle(pg_engine):
    async def scenario():
        job_id = await create_job(
            engine=pg_engine, symbol="AAPL", company_keyword="Apple", days=7
        )
        job = await get_job(engine=pg_engine, job_id=job_id)
        assert job.symbol == "AAPL"
        assert job.status == "pending"

        await set_job_status(
            engine=pg_engine, job_id=job_id, status="running", started_at=_now()
        )
        await set_job_status(
            engine=pg_engine, job_id=job_id, status="completed",
            result={"articles_saved": 3}, finished_at=_now(),
        )
        return await get_job(engine=pg_engine, job_id=job_id)

    done = _run(scenario())
    assert done.status == "completed"
    assert done.result == {"articles_saved": 3}


def test_get_job_missing(pg_engine):
    assert _run(get_job(engine=pg_engine, job_id=999)) is None