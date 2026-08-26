# technical-analyst

MCP server that fetches stock price data and produces a technical analysis
(trend/momentum/volatility/volume indicators, support & resistance, and a
bullish/bearish/neutral verdict with suggested stop-loss/take-profit),
for the `fifty-shades-of-agent` project.

## Setup

```bash
pip install -e ".[dev]"
cp .env.example .env      # fill in TWELVE_DATA_API_KEY and NEON_DATABASE_URL
```

Set up your own Neon database (not shared with teammates):
```bash
psql "$NEON_DATABASE_URL" -f src/technical_analyst/db/schema.sql
```

Run the server:
```bash
python main.py
```

Inspect/test tools manually in the browser:
```bash
mcp dev main.py
```

## Data providers

- **Primary: yfinance** — free, no API key.
- **Secondary: Twelve Data** — used if yfinance fails. Requires `TWELVE_DATA_API_KEY`.
- If both fail, tools return `{"error": "..."}`. There is currently **no
  stale-data fallback** — this is intentional (see project notes) and can
  be revisited later if needed.

## Tools

- `ping()` — sanity check.
- `get_price_data(symbol, interval="1d", lookback_days=90)` — raw OHLCV.
- `get_technical_analysis(symbol, interval="1d", lookback_days=90)` — full
  report; persists to Neon on success (history + latest snapshot).
- `get_analysis_history(symbol, limit=10)` — past reports for a symbol,
  most recent first (context for the combining agent).

## Storage (your own Neon instance)

- `price_candles` — raw OHLCV, deduped via `(symbol, interval, ts)`.
- `technical_analysis_reports` — append-only history, one row per run.
- `latest_technical_analysis` — one row per symbol, always the newest report.

## Tests

```bash
pytest
```
(Generate `tests/fixtures/sample_ohlcv.json` first — see `tests/fixtures/README.md`.)
