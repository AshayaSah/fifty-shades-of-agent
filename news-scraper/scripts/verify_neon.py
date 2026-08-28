"""Verify data landed in Neon DB."""
from news_scraper.server import get_news, get_sentiment_summary

print("=== AAPL articles in DB ===")
articles = get_news("AAPL", days=7)
print(f"{len(articles)} articles\n")
for a in articles:
    orgs = list(a["entities"].get("orgs", []))[:3] if a["entities"] else []
    print(f"  [{a['sentiment_score']:+.2f}] {a['source']}: {a['title'][:70]}")
    print(f"    event: {a['event_type']}  orgs: {orgs}")

print()
print("=== Sentiment summary ===")
summary = get_sentiment_summary("AAPL", days=7)
for k, v in summary.items():
    print(f"  {k}: {v}")
