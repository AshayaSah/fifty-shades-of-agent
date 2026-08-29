import asyncio
import logging
import os
import queue as _queue
import threading
from datetime import datetime, timezone
from pathlib import Path

from news_scraper import db, extraction, sentiment, sources

_MAX_ARTICLES = 15


def queue_logger() -> logging.Logger:
    """Job/queue logger writing to ./logs/queue.log (relative to CWD).

    Relative paths break on Vercel (no CWD writable), so the directory is
    created under the current working directory when writable and falls back
    to a temp dir otherwise.
    """
    try:
        log_dir = Path.cwd() / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        import tempfile

        log_dir = Path(tempfile.mkdtemp(prefix="news-scraper-logs-"))
        log_dir.mkdir(parents=True, exist_ok=True)

    log_file = log_dir / "queue.log"

    handler = logging.FileHandler(
        str(log_file),
        mode="a",
        encoding="utf-8",
    )
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)

    # Prevent duplicate handlers if this module is imported/reloaded
    if not logger.handlers:
        logger.addHandler(handler)

    logger.propagate = False

    return logger


queue_logger = queue_logger()


def _now():
    return datetime.now(timezone.utc)


async def execute_scrape(symbol: str, company_keyword: str, days: int = 30) -> dict:
    """Run a complete scrape + analysis pipeline for one job.

    BBC and NewsAPI fetches run in parallel, sentiment is scored as one batch,
    each article is analyzed with a single spaCy parse (parallelized across
    articles), and all rows are written in one async batched insert.
    """
    loop = asyncio.get_running_loop()
    bbc, newsapi = await asyncio.gather(
        loop.run_in_executor(None, sources.fetch_bbc, company_keyword),
        loop.run_in_executor(None, sources.fetch_newsapi, company_keyword, days),
    )

    all_articles = (bbc + newsapi)[:_MAX_ARTICLES]

    texts_for_sentiment = [a["text"] for a in all_articles]
    batch_scores = await loop.run_in_executor(
        None, sentiment.score_texts, texts_for_sentiment
    )

    # spaCy parsing + entity scoring are CPU-bound: more concurrent submissions
    # than cores just thrashes the GIL/CPU. Cap at the core count.
    sem = asyncio.Semaphore(max(1, os.cpu_count() or 2))

    async def _analyze(text):
        async with sem:
            return await loop.run_in_executor(None, extraction.analyze_article, text)

    analyzed = await asyncio.gather(*[_analyze(t) for t in texts_for_sentiment])

    rows = []
    event_counts = {}
    for i, article in enumerate(all_articles):
        entities, event_type, entity_scores = analyzed[i]
        score = batch_scores[i]
        event_counts[event_type] = event_counts.get(event_type, 0) + 1
        rows.append(
            (
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
            )
        )

    await db.save_articles(articles=rows)

    return {
        "symbol": symbol,
        "articles_found": len(bbc + newsapi),
        "articles_saved": len(rows),
        "full_text_scraped": 0,
        "event_breakdown": event_counts,
    }


class JobQueue:
    """In-process async queue with a single daemon worker.

    Tools enqueue a job_id and return immediately; the worker runs each job
    serially so long-running scrapes never block the MCP server or exceed
    proxy timeouts. Job status is persisted in the database.
    """

    def __init__(self, maxsize: int = 64):
        self._queue: "_queue.Queue[int | None]" = _queue.Queue(maxsize=maxsize)
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self):
        self._thread = threading.Thread(
            target=self._run, name="news-scraper-worker", daemon=True
        )
        self._thread.start()

    def enqueue(self, job_id: int, job_uuid=None) -> bool:
        """Queue a job. Returns False if the queue is already full."""
        try:
            self._queue.put_nowait(job_id)
        except _queue.Full:
            return False
        queue_logger.info("enqueue job_id=%s job_uuid=%s", job_id, job_uuid)
        return True

    def stop(self, timeout: float = 5.0):
        self._stop.set()
        try:
            self._queue.put_nowait(None)
        except queue.Full:
            pass
        if self._thread:
            self._thread.join(timeout=timeout)

    def _run(self):
        asyncio.run(self._aloop())

    async def _aloop(self):
        while not self._stop.is_set():
            try:
                job_id = await asyncio.to_thread(self._queue.get, True, 0.5)
            except _queue.Empty:
                continue
            if job_id is None:
                break
            try:
                await self._process(job_id)
            finally:
                self._queue.task_done()

    async def _process(self, job_id: int):
        job = await db.get_job(job_id=job_id)
        if job is None:
            return
        await db.set_job_status(job_id=job_id, status="running", started_at=_now())
        queue_logger.info(
            "run job_id=%s job_uuid=%s symbol=%s company_keyword=%s days=%s",
            job_id,
            job.job_uuid,
            job.symbol,
            job.company_keyword,
            job.days,
        )
        try:
            result = await execute_scrape(job.symbol, job.company_keyword, job.days)
        except Exception as exc:  # noqa: BLE001 - report any failure on the job
            await db.set_job_status(
                job_id=job_id, status="failed", error=str(exc), finished_at=_now()
            )
            queue_logger.error(
                "fail job_id=%s job_uuid=%s error=%s", job_id, job.job_uuid, exc
            )
            return
        await db.set_job_status(
            job_id=job_id, status="completed", result=result, finished_at=_now()
        )
        queue_logger.info(
            "complete job_id=%s job_uuid=%s articles_found=%s articles_saved=%s",
            job_id,
            job.job_uuid,
            result.get("articles_found"),
            result.get("articles_saved"),
        )


queue = JobQueue()
