"""Diagnose what sources return and why scraping is slow."""
from news_scraper.sources import fetch_bbc, fetch_newsapi, scrape_article_text
import time

print("=== BBC ===")
bbc = fetch_bbc("Apple")
print(f"  {len(bbc)} articles matched 'Apple'")
for a in bbc:
    print(f"  - {a['title'][:80]}")
    print(f"    url: {a['url'][:80]}")

print()
print("=== NewsAPI ===")
api = fetch_newsapi("Apple", days=7)
print(f"  {len(api)} articles")
for a in api[:5]:
    print(f"  - {a['title'][:80]}")
    print(f"    url: {a['url'][:80]}")

print()
print("=== Full text scrape speed test (first 3 URLs) ===")
all_urls = [a["url"] for a in (bbc + api) if a["url"]][:3]
for url in all_urls:
    t = time.time()
    text = scrape_article_text(url)
    elapsed = time.time() - t
    chars = len(text) if text else 0
    print(f"  {chars} chars in {elapsed:.1f}s - {url[:60]}")
