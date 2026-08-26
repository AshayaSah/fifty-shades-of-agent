"""Full end-to-end verify: scrape -> Neon -> read back."""
import sys
sys.stdout.reconfigure(encoding="utf-8")

from news_scraper.server import scrape_news, get_news, get_sentiment_summary

result = scrape_news("AAPL", "Apple", days=7)
print("SCRAPED:", result)
print()

articles = get_news("AAPL", days=7)
print(str(len(articles)) + " articles in Neon:")
for a in articles[:10]:
    orgs = list(a["entities"].get("orgs", []))[:3] if a["entities"] else []
    score = a["sentiment_score"]
    title = a["title"][:70]
    source = a["source"]
    event = a["event_type"]
    print("  [{:+.2f}] {}: {}".format(score, source, title))
    print("    event={}  orgs={}".format(event, orgs))

print()
summary = get_sentiment_summary("AAPL", days=7)
print("SUMMARY:", summary)
