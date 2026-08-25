"""Manual smoke test — run this by hand after adding your real NEWSAPI_KEY to .env."""

from news_scraper.sources import fetch_bbc, fetch_newsapi

KEYWORD = "Apple"

print("=" * 60)
print(f"BBC results for '{KEYWORD}':")
print("=" * 60)
bbc = fetch_bbc(KEYWORD)
if not bbc:
    print("  (no matches)")
for item in bbc:
    print(f"  [{item['published_at']}] {item['title']}")
    print(f"    {item['url']}")

print()
print("=" * 60)
print(f"NewsAPI results for '{KEYWORD}' (last 7 days):")
print("=" * 60)
try:
    news = fetch_newsapi(KEYWORD, days=7)
    if not news:
        print("  (no matches)")
    for item in news:
        print(f"  [{item['source']}] {item['title']}")
        print(f"    {item['url']}")
except Exception as e:
    print(f"  Error: {e}")
    print("  (make sure NEWSAPI_KEY is set in .env)")
