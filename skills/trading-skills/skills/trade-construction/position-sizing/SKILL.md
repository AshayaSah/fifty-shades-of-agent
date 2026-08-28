---
name: position-sizing
description: Compute a conservative MT5 position size for the fifty-shades-of-agent portfolio from account equity, risk budget, entry, stop, and the trader server's max risk guard, expressed as risk_percent for execute_trade.
---

# Position Sizing

Use this skill when the user needs a conservative risk budget for a trade on the
Exness MT5 account. The server computes lots from `risk_percent`; this skill
helps pick that number honestly.

## Role

Act like a risk-budget clerk. You convert intent (how much to risk) into the one
input the execution layer accepts (`risk_percent`), never exceeding the guard.

## When to use it

Use it when the user wants to:

- turn "risk 1%" into the value to pass to `execute_trade`
- check a planned risk against `max_risk_percent`
- size a trade after the stop is stable

## Inputs and context

Ask for:

- account equity (or let the skill pull `get_account_info`)
- risk budget as percent of equity (default conservative 0.5–1.0%)
- entry and stop (to derive SL distance)

Use the user's materials first.

## If critical data is missing

If the user gives equity + entry + stop + risk%, compute directly.

Otherwise pull `trader.get_account_info()` for equity and `get_safety_config()`
for `max_risk_percent`. Use `technical-analyst.get_technical_analysis` for a
suggested SL if the user has none.

## Analysis process

1. **Equity.** Use supplied equity or `get_account_info().equity`.
2. **Risk cap.** Read `max_risk_percent` (2.0). If the user's budget exceeds it,
   cap and flag.
3. **SL distance.** `|entry - stop|`. If missing, borrow the technical
   `suggested_stop_loss` as a starting stop and say so.
4. **Risk amount.** `equity * risk_percent / 100`.
5. **Output.** Return `risk_percent` to pass to `execute_trade`, plus the dollar
   risk and implied SL distance. The server turns this into lots; you do not.
6. **Sanity.** If SL distance is near zero (entry == stop), refuse and ask for a
   real stop.

## Core Assessment Framework

- **Within guard**: `risk_percent <= max_risk_percent`.
- **Stop real**: SL distance materially larger than spread.
- **Conservative default**: 0.5–1.0% unless the user states more.

## Evidence That Would Invalidate This Analysis

- equity unknown and `get_account_info` fails
- stop equals entry (no risk defined)
- requested risk above `max_risk_percent` with no guard override possible

## Output structure

1. `Summary` — recommended `risk_percent`
2. `Inputs` — equity, entry, stop, budget
3. `Risk` — dollar risk and SL distance
4. `Guard check` — vs `max_risk_percent`
5. `Caveats` — stop source, freshness

## Best practices

- default conservative; let the user raise it
- never imply you set lot size — the server does
- if no stop, suggest one; do not size blind

## Usage examples

- "Use `position-sizing` for a $10,000 account risking 1% with entry 198.60 and stop 189.30."
- "Use `position-sizing` on my AAPLm plan before execute_trade."
