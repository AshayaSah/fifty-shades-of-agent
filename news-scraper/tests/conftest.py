import asyncio
import os

import pytest
from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from news_scraper.models import Base

load_dotenv()

_DEFAULT_TEST_URL = (
    "postgresql+psycopg://postgres:news-scraper-test"
    "@localhost:15432/news_scraper_test"
)


def _normalized(url: str) -> str:
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg://", 1)
    return url


def _admin_url(test_url: str) -> str:
    return test_url.rsplit("/", 1)[0] + "/postgres"


TEST_DATABASE_URL = _normalized(
    os.environ.get("TEST_DATABASE_URL", _DEFAULT_TEST_URL)
)


async def _ensure_database():
    admin = create_async_engine(_admin_url(TEST_DATABASE_URL), isolation_level="AUTOCOMMIT")
    try:
        async with admin.connect() as conn:
            exists = await conn.scalar(
                text(
                    "SELECT 1 FROM pg_database WHERE datname = 'news_scraper_test'"
                )
            )
            if not exists:
                await conn.execute(text("CREATE DATABASE news_scraper_test"))
    finally:
        await admin.dispose()


async def _reset(engine):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)


@pytest.fixture
def pg_engine():
    try:
        asyncio.run(_ensure_database())
    except Exception as exc:  # pragma: no cover - depends on local infra
        pytest.skip(f"no test PostgreSQL available ({exc}); "
                    "start one with scripts/up_test_db.sh")

    engine = create_async_engine(TEST_DATABASE_URL)
    try:
        asyncio.run(_reset(engine))
    except Exception as exc:  # pragma: no cover - depends on local infra
        asyncio.run(engine.dispose())
        pytest.skip(f"test PostgreSQL unreachable ({exc})")

    yield engine

    try:
        asyncio.run(_reset(engine))
    finally:
        asyncio.run(engine.dispose())