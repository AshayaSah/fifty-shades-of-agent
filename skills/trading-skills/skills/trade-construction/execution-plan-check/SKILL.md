---
name: execution-plan-check
description: Review whether a trade plan is operationally executable on the fifty-shades-of-agent Exness MT5 book by checking symbol resolution, order logic, safety guards, proposal expiry, and position capacity before propose_trade/execute_trade are called.
---

# Execution Plan Check

Use this skill when the user has a trade plan and wants to know whether it can
actually be implemented cleanly on the MT5 account, not whether the idea is good.

## Role

Act like a trading-desk operations check. You verify the plan survives the
system's real constraints before any order is staged.

## When to use it

Use it when the user wants to:

- confirm a plan is executable before staging it
- know why `propose_trade` / `execute_trade` might reject them
- pre-flight a plan across symbol, guards, and capacity

## Inputs and context

Ask for:

- the symbol or name, direction, entry, SL, TP
- intended `risk_percent`

Use the user's materials first.

## If critical data is missing

If enough, do nothing external. Otherwise use the portfolio providers:

- `trader.resolve_symbol(query)` — must return a live instrument
- `trader.get_safety_config()` — limits + kill switch
- `trader.get_account_info()` + `trader.get_positions()` — capacity
- `technical-analyst.get_technical_analysis` — SL/TP realism vs structure

## Analysis process

1. **Resolve.** `resolve_symbol` must succeed. No match -> not executable.
2. **Structure realism.** SL/TP must sit outside spread and near technical
   support/resistance from `get_technical_analysis`. A stop inside the candle
   body is unrealistic.
3. **Guard pre-check.** `get_safety_config()`: kill switch off, `risk_percent <=
   max_risk_percent` (2.0), open positions `< max_concurrent_positions` (3).
4. **Expiry awareness.** A `propose_trade` is valid only 15 minutes. If the user
   staged earlier, re-propose.
5. **Capacity.** If at 3 positions, execution will be rejected; plan a close
   first via `close_position`.
6. **Verdict.** Executable / executable-with-changes / not-executable, with the
   exact blocker named.

## Core Assessment Framework

- **Resolvable**: a real MT5 symbol exists.
- **Guarded**: within kill-switch, risk %, and position limits.
- **Realistic**: SL/TP survive spread and structure.

## Evidence That Would Invalidate This Analysis

- `resolve_symbol` returns no match
- kill switch on at execution time
- proposal older than 15 minutes when `execute_trade` is called

## Output structure

1. `Summary` — executable / with-changes / not-executable
2. `Symbol` — resolved instrument
3. `Guards` — safety config state
4. `Structure` — SL/TP realism vs technical
5. `Blockers` — exact reasons if not executable
6. `Caveats` — expiry, freshness

## Best practices

- name the exact tool that will reject, not a vague warning
- never suggest bypassing a guard
- re-propose stale plans rather than executing expired ones

## Usage examples

- "Use `execution-plan-check` on my plan to buy AAPLm at 198.60 and tell me if it's executable."
- "Use `execution-plan-check` before I stage gold."
