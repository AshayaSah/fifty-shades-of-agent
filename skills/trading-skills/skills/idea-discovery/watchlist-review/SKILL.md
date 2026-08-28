---
name: watchlist-review
description: Review a watchlist for the fifty-shades-of-agent portfolio and rank which names deserve active attention, background monitoring, or removal by running news-scraper sentiment and technical-analyst verdict across each symbol and weighing catalysts, tradability, and redundancy.
---

# Watchlist Review

Use this skill when the user starts with too many names and needs triage before
any `pre-trade-check` or `propose_trade`.

## Role

Act like a watchlist curator. You thin the list to what is worth the user's
attention, using the portfolio providers per name.

## When to use it

Use it when the user wants to:

- rank a list of tickers for the week
- drop redundant or dead names
- find which names have a real setup forming

## Inputs and context

Ask for:

- the list of symbols or names
- the user's style and timeframe (default swing / daily)

Use the user's materials first.

## If critical data is missing

If the user gives the list, run the providers per symbol (cap calls sensibly):

- `trader.resolve_symbol` each name to confirm tradability
- `news-scraper.get_sentiment_summary` + `get_sentiment_trend` for event heat
- `technical-analyst.get_technical_analysis` for verdict + SR

## Analysis process

1. **Resolve all.** `resolve_symbol` per name. Untradable names -> flag/remove.
2. **Score each.** For every resolvable name combine:
   - technical verdict (bullish/bearish/neutral + confidence)
   - sentiment trend (improving/flat/deteriorating)
   - upcoming catalyst density from news events
3. **Rank.** Active attention = aligned technical + sentiment + near catalyst.
   Background = one weak leg. Remove = conflicting legs or untradable.
4. **Redundancy.** Group by sector/theme; if three names say the same thing,
   keep the cleanest setup, monitor the rest.
5. **Output.** A ranked table with a one-line reason each.

## Core Assessment Framework

- **Setup quality**: technical + sentiment agree and a catalyst is dated.
- **Tradability**: symbol resolves to a live MT5 instrument.
- **Non-redundancy**: not three copies of one theme.

## Evidence That Would Invalidate This Analysis

- a name fails `resolve_symbol` (not tradable in this book)
- providers return no data for a name the user assumed was covered
- sentiment/technical disagree with no way to weigh them

## Output structure

1. `Summary` — counts per bucket
2. `Active` — names to watch now + why
3. `Background` — names to monitor
4. `Drop` — names to remove + why
5. `Caveats` — coverage, freshness, disclosure

## Best practices

- be willing to drop names; a shorter list is the point
- disclose per-name provider source
- prefer the cleanest setup among redundant names

## Usage examples

- "Use `watchlist-review` on these semis for next week and tell me what deserves attention."
- "Use `watchlist-review` on my gold + EURUSD + AAPL list."
