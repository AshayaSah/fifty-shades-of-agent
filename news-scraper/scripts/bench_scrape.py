"""Timing test — run with: uv run python scripts/bench_scrape.py"""

import time

t0 = time.time()
print("1. Loading modules...")
from news_scraper import sources, sentiment, extraction
print(f"   Done in {time.time() - t0:.1f}s\n")

t1 = time.time()
print("2. Fetching BBC feed...")
bbc = sources.fetch_bbc("Apple")
print(f"   Got {len(bbc)} articles in {time.time() - t1:.1f}s\n")

t2 = time.time()
print("3. Scraping full text for first article...")
if bbc:
    ft = sources.scrape_article_text(bbc[0]["url"])
    print(f"   Got {len(ft) if ft else 0} chars in {time.time() - t2:.1f}s\n")
else:
    print("   Skipped (no articles)\n")

text = bbc[0]["text"] if bbc else "Apple reported strong earnings."

t3 = time.time()
print("4. FinBERT sentiment (single)...")
score = sentiment.score_text(text)
print(f"   Score: {score:.4f} in {time.time() - t3:.1f}s\n")

t4 = time.time()
print("5. FinBERT sentiment (batch of 3)...")
scores = sentiment.score_texts([text, text, text])
print(f"   Scores: {[f'{v:.4f}' for v in scores.values()]} in {time.time() - t4:.1f}s\n")

t5 = time.time()
print("6. spaCy entity extraction...")
entities = extraction.extract_entities(text)
print(f"   Entities: {entities} in {time.time() - t5:.1f}s\n")

t6 = time.time()
print("7. spaCy sentence split...")
import spacy
nlp = spacy.load("en_core_web_sm")
doc = nlp(text[:10000])
sents = [s.text for s in doc.sents]
print(f"   {len(sents)} sentences in {time.time() - t6:.1f}s\n")

t7 = time.time()
print("8. Per-entity scoring...")
escores = extraction.score_entities(text, entities)
print(f"   {escores} in {time.time() - t7:.1f}s\n")

print(f"TOTAL: {time.time() - t0:.1f}s")
