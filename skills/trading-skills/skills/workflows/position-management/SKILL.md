---
name: position-management
description: Decide hold / trim / tighten / exit on an open MT5 position by checking live price against thesis, invalidation, and catalyst risk.
---

# Position Management

Use this skill while a trade is open and the user wants a hold / trim / tighten /
exit decision rather than guesswork.

## Role

Act like a disciplined position manager. You compare the live position against
what was promised at entry and flag drift early.

## When to use it

Use it when the user wants to:

- decide what to do with an open position right now
- know if the original thesis is still intact
- set or move a trailing / tighter stop

## Inputs and context

Ask for:

- the open ticket or symbol
- the original thesis and invalidation (from the Trade Context if available)
- the original entry / stop / target

Use the user's materials first.

## If critical data is missing

If enough, do nothing external.

Otherwise pull:

- `trader.get_positions()` to locate the ticket, symbol, volume, profit
- `technical-analyst.get_technical_analysis(resolved_symbol)` for current verdict
  and `suggested_stop_loss`
- `news-scraper.get_sentiment_summary` + `get_sentiment_trend` for catalyst risk
- `trader.resolve_symbol` if only a name was given

## Analysis process

1. **Locate.** Find the position via `get_positions()` (or `resolve_symbol` then
   match). Capture current profit, open price, live SL/TP if set.
2. **Thesis check.** Compare current price action and `get_technical_analysis`
   verdict against the original thesis. Has the verdict flipped? Is price through
   the original invalidation level?
3. **Catalyst check.** Pull `get_sentiment_trend`. Is a negative event landing
   inside the hold period that the plan did not account for?
4. **Risk check.** Is the trade still within `max_risk_percent` (2.0) and is the
   book within `max_concurrent_positions` (3)?
5. **Decide.** Hold / trim / tighten / exit, with the trigger made explicit.

## Core Assessment Framework

- **Thesis intact**: verdict agrees with direction and price above invalidation -> hold.
- **Thesis strained**: verdict flipped or price at invalidation -> tighten or exit.
- **Catalyst surprise**: new negative event before target -> trim or tighten.

## Evidence That Would Invalidate This Analysis

- ticket not found in `get_positions()` (already closed)
- technical provider returns insufficient history for the symbol
- kill switch engaged mid-review (execution blocked regardless)

## Output structure

1. `Summary` — hold / trim / tighten / exit
2. `Position state` — ticket, P&L, current SL/TP
3. `Thesis status` — intact / strained / broken
4. `Catalyst risk` — upcoming dated events
5. `Action` — concrete adjustment, with trigger
6. `Caveats` — data freshness, limit state

## Best practices

- tighten risk by proposing a new `propose_trade` only as a plan; closing uses
  `trader.close_position`
- never recommend adding risk beyond guards
- keep the original invalidation as the hard line

## Usage examples

- "Use `position-management` on my EURUSDm long and tell me hold or exit."
- "Use `position-management` on ticket 123456 before the earnings print."
