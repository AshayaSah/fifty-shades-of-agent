---
name: pre-trade-check
description: Pre-trade go/no-go gate: route a trade idea through news sentiment, technical verdict, and MT5 risk guards before propose_trade.
---

# Pre-Trade Check

Use this skill when the user has a trade idea or watchlist entry and wants one
readiness verdict instead of manually running each layer.

This skill does **not** place orders. It ends with a `proposal_id` only when the
trade is ready and the user explicitly approves execution.

## Role

Act like a conservative execution analyst. Your job is to confirm the idea has
passed news, technical, and risk gates before it touches the Exness MT5 account.

## When to use it

Use it when the user wants to:

- confirm a single trade idea is ready before risking capital
- catch a missing layer (no sentiment, no technical, no invalidation) early
- get a staged `proposal_id` they can execute or discard

## Inputs and context

Ask for:

- the symbol or human-friendly name (e.g. "Apple", "gold")
- intended direction (buy/sell) and timeframe
- the user's own thesis and invalidation, if they have one

Helpful but optional:

- planned entry / stop / target
- account risk budget for this trade

Use the user's materials first.

## If critical data is missing

If the user's material is enough, do not fetch anything.

If you need market context, use the portfolio providers in this order:

1. `trader.resolve_symbol(query)` to get the exact MT5 symbol.
2. `news-scraper.get_sentiment_summary(symbol)` + `get_sentiment_trend(symbol)`
   for the news layer.
3. `technical-analyst.get_technical_analysis(symbol)` for the technical verdict.

Full tool inventory in `references/portfolio-data-providers.md`.

## Analysis process

1. **Resolve.** Call `trader.resolve_symbol`. If no match, stop and ask the user.
2. **News gate.** Pull `get_sentiment_summary` + `get_sentiment_trend`. Flag if
   sentiment is strongly negative (`< -0.15`) or deteriorating into a known
   catalyst — that is a ready-to-fail condition unless the thesis explains it.
3. **Technical gate.** Pull `get_technical_analysis`. Note `verdict`,
   `confidence`, `suggested_stop_loss`, `suggested_take_profit`. Use
   `get_analysis_history` if you suspect a recent flip.
4. **Structure check.** If the user gave entry/sl/tp, run
   `risk-reward-sanity-check` logic: SL must sit outside noise (use the
   technical `suggested_stop_loss` as a sanity anchor), target beyond
   resistance/support. If no structure given, propose the technical SL/TP as a
   starting point.
5. **Risk gate.** Call `trader.get_safety_config()` and `get_account_info()`.
   Confirm `kill_switch` is off, `risk_percent <= max_risk_percent` (2.0), and
   open positions `< max_concurrent_positions` (3).
6. **Stage.** If all gates pass, call `trader.propose_trade(symbol, direction,
   entry, sl, tp, rationale)` and return the `proposal_id`. Do **not** call
   `execute_trade` unless the user explicitly says go.

## Core Assessment Framework

- **News–technical agreement**: both non-conflicting (e.g. positive sentiment +
  bullish verdict) is green; direct conflict is red until resolved.
- **Structure coherence**: entry between support and resistance, SL beyond
  structure, R-multiple >= 1.0.
- **Capacity headroom**: enough risk budget and position slots remain.

## Evidence That Would Invalidate This Analysis

- `kill_switch` is on, or `get_safety_config` shows risk/position limits already hit
- sentiment strongly negative with no thesis-based explanation
- technical verdict bearish against a long idea (or vice versa)
- cannot resolve the symbol to a live MT5 instrument

## Output structure

1. `Summary` — ready / not_ready / rework
2. `News layer` — sentiment, trend, key events, source
3. `Technical layer` — verdict, confidence, SL/TP anchors
4. `Risk gate` — safety config, headroom, proposal_id (if staged)
5. `Open items` — what is missing before execution
6. `Caveats` — data freshness, provider disclosure

## Best practices

- never call `execute_trade` unprompted
- disclose each provider and its freshness
- if one layer fails, say not_ready; do not average it away

## Usage examples

- "Use `pre-trade-check` on my AAPL swing long and tell me if it's actually ready."
- "Use `pre-trade-check` on gold before I commit risk."
