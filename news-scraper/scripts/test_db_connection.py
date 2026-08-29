"""Manual DB smoke test — run by hand after confirming DATABASE_URL in .env."""

import asyncio
from datetime import datetime, timezone

from news_scraper.db import fetch_articles, init_db, save_article

TEST_URL = "https://example.com/test-article-dedup"
SYMBOL = "TESTSYM"


async def main():
    print("1. Initializing database table...")
    await init_db()
    print("   Done.\n")

    print("2. Saving fake article...")
    await save_article(
        symbol=SYMBOL,
        source="TestSource",
        title="Fake article for dedup test",
        url=TEST_URL,
        published_at=datetime.now(timezone.utc),
        sentiment_score=0.42,
    )
    rows = await fetch_articles(symbol=SYMBOL)
    print(f"   Articles after first insert: {len(rows)}")
    for row in rows:
        print(f"     {row}\n")

    print("3. Saving same article again (same URL)...")
    await save_article(
        symbol=SYMBOL,
        source="TestSource",
        title="Fake article for dedup test",
        url=TEST_URL,
        published_at=datetime.now(timezone.utc),
        sentiment_score=0.42,
    )
    rows = await fetch_articles(symbol=SYMBOL)
    print(f"   Articles after second insert: {len(rows)}")
    print(f"   ON CONFLICT dedup working: {len(rows) == 1}")


if __name__ == "__main__":
    asyncio.run(main())