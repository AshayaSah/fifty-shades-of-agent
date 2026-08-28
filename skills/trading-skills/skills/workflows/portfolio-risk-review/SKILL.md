---
name: portfolio-risk-review
description: Whole-book risk review: concentration, correlation, catalyst clustering, and live MT5 fragility before adding or keeping exposure.
---

# Portfolio Risk Review

Use this skill when the user needs a whole-book risk view of their live Exness
MT5 book before adding or maintaining exposure.

## Role

Act like a portfolio risk officer. Conservative, explicit about concentration
and correlation, never a cheerleader for more risk.

## When to use it

Use it when the user wants to:

- see concentration and correlation before adding a new position
- check whether open MT5 positions are too fragile into a catalyst cluster
- a pre-weekend or pre-event book health check

## Inputs and context

Ask for:

- the list of open positions (or let the skill pull them)
- any planned additions and their symbols
- the user's risk budget and correlation concerns

Use the user's materials first.

## If critical data is missing

If the user's material is enough, do not fetch anything.

Otherwise use the portfolio providers:

- `trader.get_positions()` and `trader.get_account_info()` for the live book
- `trader.get_safety_config()` for hard limits
- `news-scraper.get_sentiment_summary` / `get_sentiment_trend` per symbol for
  catalyst clustering
- `technical-analyst.get_technical_analysis` per symbol for fragility

## Analysis process

1. **Snapshot the book.** `get_positions()` + `get_account_info()`. Note count
   vs `max_concurrent_positions` (3) and margin headroom.
2. **Concentration.** Group open symbols by issuer, sector, and correlated
   theme. If one cluster dominates notional or margin, flag it.
3. **Catalyst clustering.** For each open symbol, pull recent
   `get_sentiment_summary` + `get_sentiment_trend`. Flag names with negative or
   deteriorating sentiment and any dated event that lands inside the holding
   period.
4. **Fragility.** For each open symbol, pull `get_technical_analysis`. Note
   verdict flips or SL breaches vs current price.
5. **Capacity.** Compare planned additions against remaining risk budget and
   position slots from `get_safety_config()`.
6. **Verdict.** Recommend hold / trim / tighten / reduce with concrete symbols.

## Core Assessment Framework

- **Concentration**: no single cluster should exceed a share of margin the user
  is uncomfortable losing in one move.
- **Correlation**: positions that move together inflate risk beyond the position
  count suggests.
- **Catalyst overlap**: many positions expiring into the same event = bundled
  tail risk.

## Evidence That Would Invalidate This Analysis

- `get_positions()` returns stale or zero rows while the user believes they are
  holding
- sentiment/technical providers unavailable for a key open symbol
- account equity changed materially since last snapshot

## Output structure

1. `Summary` — book health verdict
2. `Live book` — positions, equity, margin, slots used
3. `Concentration` — clusters and their weight
4. `Catalyst cluster` — dated risks per symbol
5. `Fragility` — technical red flags
6. `Recommendation` — hold / trim / tighten / reduce
7. `Caveats` — data freshness, kill-switch state

## Best practices

- disclose the kill-switch and limit state explicitly
- separate "tighten risk" (move SL) from "reduce" (close)
- never recommend exceeding `max_risk_percent` or `max_concurrent_positions`

## Usage examples

- "Use `portfolio-risk-review` on my open book before I add more semis."
- "Use `portfolio-risk-review` ahead of the FOMC print."
