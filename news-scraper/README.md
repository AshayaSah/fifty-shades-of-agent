# News Scraper

A Python MCP (Model Context Protocol) server that scrapes company news, analyzes financial sentiment, extracts entities and event types, and persists everything to Postgres — ready to be plugged into agents via the **streamable-http** transport.

Built as the news-intelligence layer for a trading-agent hackathon project.

---

## Features

- **Multi-source ingestion** — pulls news from the BBC Business RSS feed and the NewsAPI `everything` endpoint (matched via `qInTitle` for company relevance).
- **Financial sentiment analysis** — scores every headline, summary, and entity using **FinBERT** (`ProsusAI/finbert`) on a `-1` (bearish) to `+1` (bullish) scale. Batch scoring runs in a single forward pass for speed; the model is lazy-loaded on first use.
- **Entity extraction** — spaCy (`en_core_web_sm`) named-entity recognition extracts organizations, people, and locations from each article.
- **Per-entity sentiment** — each extracted entity gets its own FinBERT score, so you can see exactly *who* is associated with positive or negative coverage.
- **Event classification** — a keyword-rule classifier tags each article with the primary event type:
  `earnings`, `lawsuit`, `acquisition`, `product_launch`, `market_movement`, `executive`, `regulation`, `other`.
- **Postgres persistence** — deduplicated storage (via `ON CONFLICT (url)`) in Neon Postgres, with **JSONB** columns for entities and entity sentiment.
- **MCP-native** — five tools exposed over `streamable-http`, consumable by any MCP client (Trueforge, Claude, the MCP Inspector, etc.).

---

## How It Works

```
                    ┌────────────────────────────────────────────────────┐
                    │                     MCP Client                     │
                    │              (Trueforge / Claude / ...)            │
                    └───────────────────────────┬────────────────────────┘
                                                │   streamable-http (JSON-RPC)
                                                 ▼
                    ┌────────────────────────────────────────────────────┐
                    │          FastMCP Server  (0.0.0.0:8000/mcp/)      │
                    │                                                    │
                    │   scrape_news ────▶ fetch_bbc + fetch_newsapi     │
                    │        │                                          │
                    │        ├──▶ FinBERT sentiment (article-level)     │
                    │        ├──▶ spaCy NER (orgs, people, locations)   │
                    │        ├──▶ FinBERT (per-entity sentiment)        │
                    │        └──▶ event classifier (keyword rules)      │
                    │                          │                         │
                    │                          ▼                         │
                    │              save_articles (batch insert)          │
                    └───────────────────────────┬────────────────────────┘
                                                │   read-only queries
                                                 ▼
                    ┌────────────────────────────────────────────────────┐
                    │            Neon Postgres  (news_articles)          │
                    └────────────────────────────────────────────────────┘
```

When a client calls `scrape_news`, the pipeline fetches, enriches, and stores articles in one pass; the remaining tools (`get_news`, `get_sentiment_summary`, `get_sentiment_trend`, `get_source_comparison`) read the enriched data back for the agent to reason over.

---

## Tech Stack

| Component     | Technology                                              |
| ------------- | ------------------------------------------------------- |
| Language      | Python 3.14, managed with `uv`                          |
| MCP server    | `mcp[cli]` (FastMCP) — `streamable-http` transport      |
| Sentiment     | Hugging Face Transformers + **FinBERT** (PyTorch)       |
| Entities      | spaCy `en_core_web_sm`                                  |
| News sources  | `feedparser` (BBC RSS) · `requests` (NewsAPI) · `trafilatura` (full-text) |
| Database      | `psycopg[binary]` + Neon Postgres                       |
| Config        | `python-dotenv` (`.env`)                                |
| QA            | `pytest` (29 tests)                                     |

---

## MCP Tools

| Tool                      | Description                                                                        |
| ------------------------- | ---------------------------------------------------------------------------------- |
| `scrape_news`             | Scrape news for a ticker + company name, run the full analysis pipeline, save to DB |
| `get_news`                | Retrieve previously scraped articles for a symbol                                   |
| `get_sentiment_summary`   | Aggregate stats: article count, average sentiment, event breakdown, per-entity scores |
| `get_sentiment_trend`     | Daily average-sentiment series, most recent first (momentum spotting)               |
| `get_source_comparison`   | Average sentiment by news source, sorted most-positive first                        |

### Example call

```python
# scrape_news(symbol="AAPL", company_keyword="Apple", days=7)
{
  "symbol": "AAPL",
  "articles_found": 98,
  "articles_saved": 15,
  "full_text_scraped": 0,
  "event_breakdown": {
    "product_launch": 4,
    "other": 8,
    "lawsuit": 1,
    "market_movement": 1,
    "regulation": 1
  }
}
```

---

## Getting Started

### 1. Prerequisites

- Python **3.14** and [`uv`](https://docs.astral.sh/uv/)
- A Neon Postgres database (`DATABASE_URL`)
- A [NewsAPI](https://newsapi.org/) API key (`NEWSAPI_KEY`) — free tier is fine

### 2. Setup

```bash
# Install dependencies (incl. dev group)
uv sync

# Install the spaCy model used for NER
uv run python -m spacy download en_core_web_sm

# Configure environment
copy .env.example .env
#   then fill in DATABASE_URL and NEWSAPI_KEY
```

> [!NOTE]
> The editable package install plus a one-time FinBERT download happen lazily on first sentiment call (~40 s import on a cold cache, then cached).

### 3. Run the MCP server

```bash
uv run main.py
```

The server listens on **`http://0.0.0.0:8000/mcp/`** using the `streamable-http` transport — point any MCP client (e.g. Trueforge) at that URL.

### 4. Local development / inspection

```bash
uv run mcp dev main.py        # launch with the MCP Inspector UI
uv run pytest -v              # run the 29-test suite
```

> [!TIP]
> The MCP Inspector enforces a 60 s hard timeout — `scrape_news` caps at 15 articles (`_MAX_ARTICLES`) so one call stays well within it.

---

## Environment Variables

| Variable        | Required | Description                                        |
| --------------- | -------- | -------------------------------------------------- |
| `DATABASE_URL`  | yes      | Neon Postgres connection string                    |
| `NEWSAPI_KEY`   | yes*     | NewsAPI free-tier key (*`scrape_news` uses NewsAPI) |

---

## Database Schema

Table: `news_articles`

| Column            | Type      | Notes                                      |
| ----------------- | --------- | ------------------------------------------ |
| `id`              | SERIAL    | PK                                         |
| `symbol`          | TEXT      | Ticker, e.g. `AAPL`                        |
| `source`          | TEXT      | `BBC` or NewsAPI publisher name            |
| `title`           | TEXT      | Article headline                           |
| `url`             | TEXT      | Unique — dedup via `ON CONFLICT (url)`     |
| `published_at`    | TIMESTAMP |                                            |
| `full_text`       | TEXT      | Reserved for full-body scraping            |
| `sentiment_score` | FLOAT     | FinBERT, `-1` to `+1`                      |
| `scraped_at`      | TIMESTAMP | Default `NOW()`                            |
| `entities`        | JSONB     | `{orgs, people, locations}`                |
| `event_type`      | TEXT      | Classified category (see Features)         |
| `entity_scores`   | JSONB     | `{entity_name → FinBERT score}`            |

Schema and migrations are applied automatically on server startup via idempotent `CREATE TABLE IF NOT EXISTS` / `ADD COLUMN IF NOT EXISTS` statements.

---

## Project Structure

```
news-scraper/
├── main.py                     # streamable-http entrypoint (uv run main.py)
├── pyproject.toml              # uv / project config, deps, dev group
├── .env.example                # DATABASE_URL + NEWSAPI_KEY template
├── scripts/                    # Diagnostics & verification helpers
│   ├── full_verify.py          # end-to-end: scrape → DB → read back
│   └── verify_neon.py          # inspect stored articles + sentiment
├── src/news_scraper/
│   ├── server.py               # FastMCP server + 5 MCP tools
│   ├── sources.py              # BBC RSS + NewsAPI fetchers, full-text scraper
│   ├── sentiment.py            # FinBERT lazy-load + batch scoring
│   ├── extraction.py           # spaCy NER, event classifier, entity scoring
│   └── db.py                   # Postgres CRUD, migrations, aggregation queries
└── tests/                      # 29 unit tests (sentiment, sources, extraction, DB)
```

---

## Notes & Known Limitations

- **Full-text scraping is currently disabled** by default. `trafilatura` frequently hits 403s/timeouts with no configurable timeout, so `scrape_news` analyzes the headline + summary text instead — sentiment quality is still strong for headlines. The `full_text` column remains in the schema for future re-enabling.
- **BBC RSS yields limited results** for most tickers (e.g. "Apple" matches actual fruit stories); NewsAPI is the primary volume source.
- **FinBERT import is slow on cold cache** (~40 s) but is lazy and cached in memory for subsequent calls.
- NewsAPI free tier restricts how far back you can query; `days` beyond the tier limit will just return what the API allows.