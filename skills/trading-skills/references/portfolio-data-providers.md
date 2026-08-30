# Portfolio Data Providers

These skills are built for the **fifty-shades-of-agent** trading system. The
system is three independent MCP servers that a coordinating trading agent wires
together. Each skill uses the *minimum* set of tools needed for its job. Prefer
calling these tools over inventing market data.

## 1. news-scraper (news + sentiment MCP)

Supplies the *news/sentiment* layer. FinBERT sentiment, spaCy entities, and
event classification, persisted to Postgres.

| Tool | What it gives you |
| --- | --- |
| `scrape_news(symbol, company_keyword, days=30)` | Scrape BBC + NewsAPI for a company, score sentiment, extract entities/events, persist. |
| `get_news(symbol, days=30)` | List of articles: source, title, URL, published_at, sentiment_score, entities, event_type. |
| `get_sentiment_summary(symbol, days=30)` | Aggregate: article_count, average_sentiment, event_breakdown, avg_entity_sentiment. |
| `get_sentiment_trend(symbol, days=30)` | Daily avg_sentiment + article_count, most recent first. |
| `get_source_comparison(symbol, days=30)` | Per-source avg_sentiment + article_count (bias check). |

**Interpretation notes**
- `average_sentiment` is FinBERT-scaled, roughly `[-1, +1]`. Treat `> 0.15` as
  net positive, `< -0.15` as net negative, between as mixed/neutral.
- Sentiment is *lagging and source-biased*. Always pair it with
  `get_sentiment_trend` to see momentum (improving vs deteriorating) and
  `get_source_comparison` to catch single-outlet skew.
- Event types (e.g. earnings, regulation, product) tell you *why* sentiment
  moved. Use them in catalyst reasoning, not as trade signals by themselves.

## 2. technical-analyst (price + technical MCP)

Supplies the *technical* layer. yfinance primary, Twelve Data fallback.

| Tool | What it gives you |
| --- | --- |
| `get_technical_analysis(symbol, interval="1d", lookback_days=90)` | Verdict (bullish/bearish/neutral), confidence, reasons, support/resistance, suggested_stop_loss, suggested_take_profit, indicator snapshot. |
| `get_price_data(symbol, interval="1d", lookback_days=90)` | Raw OHLCV candles. |
| `get_analysis_history(symbol, limit=10)` | Past reports, most recent first — use to see if verdict is stable or flipped. |

**Interpretation notes**
- The `verdict` is a combined signal from trend (SMA/EMA), momentum (RSI/MACD),
  volatility (Bollinger/ATR) and volume (OBV). It is *not* a forecast.
- `suggested_stop_loss` / `suggested_take_profit` are ATR-based (1.5× / 3×
  ATR). Treat them as a starting structure to sanity-check, not gospel.
- `get_analysis_history` is the cheapest way to spot regime flips before you
  trust a single snapshot.

## 3. trader (Exness MetaTrader 5 execution MCP)

Supplies the *execution + risk-guard* layer. Runs against an Exness MT5 demo
account. Safety guards are enforced server-side.

| Tool | What it gives you |
| --- | --- |
| `resolve_symbol(query)` | Turn "Apple"/"gold"/"EURUSD" into exact MT5 symbol (e.g. `AAPLm`, `XAUUSDm`, `EURUSDm`). **Always call before proposing.** |
| `propose_trade(symbol, direction, entry, sl, tp, rationale)` | Stage a pending proposal (no live order yet). Returns a `proposal_id`. |
| `execute_trade(proposal_id, risk_percent)` | Execute a pending proposal. Enforces kill switch, max risk %, position cap, expiry. |
| `get_positions()` | Open positions: ticket, symbol, volume, prices, profit, type. |
| `get_account_info()` | Balance, equity, margin, leverage. |
| `get_safety_config()` | `max_risk_percent` (2.0), `max_concurrent_positions` (3), `proposal_expiry_minutes` (15), kill-switch state. |
| `kill_switch(state)` | Halt/resume all trading. |
| `close_position(ticket)` | Close an open position by ticket. |

**Hard execution constraints (do not fight these)**
- Max risk per trade: `2.0%` of equity (`risk_percent` to `execute_trade`).
- Max `3` concurrent open positions.
- A proposal **expires after 30 minutes**; re-propose if stale.
- Kill switch ON halts everything. Check `get_safety_config()` before executing.
- Lot size is computed server-side from `risk_percent` and SL distance. You pass
  intent (entry/sl/tp/risk%), not lots.

## Wiring pattern

The cleanest agent loop:

1. Gather the user's own context first (their thesis, plan, watchlist).
2. Fill gaps with the smallest tool call above.
3. Carry a compact Trade Context (see `references/trade-context.md`) between
   skills, not raw transcript.
4. Keep execution behind `propose_trade` -> `execute_trade` and respect
   `get_safety_config()`.
5. Disclose what came from each provider and how fresh it is.
