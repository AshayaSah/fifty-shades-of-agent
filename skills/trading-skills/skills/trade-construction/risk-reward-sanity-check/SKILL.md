---
name: risk-reward-sanity-check
description: Test entry/stop/target coherence and asymmetry (R-multiple, stop placement, target realism) before propose_trade.
---

# Risk-Reward Sanity Check

Use this skill when the user wants to test whether entry/stop/target structure
is worth taking, independent of whether the idea is true.

## Role

Act like a structure critic. You judge the shape of the trade, not the narrative.

## When to use it

Use it when the user wants to:

- confirm a stop and target make sense together
- know the R-multiple before staging
- catch a stop inside noise or a target that cannot be reached

## Inputs and context

Ask for:

- entry, stop, target
- direction (buy/sell)
- optionally the technical `support`/`resistance` anchors

Use the user's materials first.

## If critical data is missing

If the user gives entry/sl/tp, compute directly.

Otherwise pull `technical-analyst.get_technical_analysis` for
`suggested_stop_loss`, `suggested_take_profit`, `support`, `resistance` to
sanity-check the user's structure against the technical read.

## Analysis process

1. **Direction math.** For a long: risk = entry - stop, reward = target - entry.
   For a short: risk = stop - entry, reward = entry - target.
2. **R-multiple.** `reward / risk`. Flag `< 1.0` as structurally unattractive;
   prefer `>= 1.5` for swings.
3. **Stop realism.** Stop should sit beyond `support` (long) / `resistance`
   (short) and beyond spread. A stop inside structure is a failure mode.
4. **Target realism.** Target should clear `resistance` (long) / `support`
   (short) with room; if target sits under the nearest barrier, flag.
5. **Asymmetry.** Note if reward is thin but risk is wide — the structure leaks
   even if the thesis is right.

## Core Assessment Framework

- **R >= 1.0** minimum; >= 1.5 preferred for swings.
- **Stop beyond structure**, not inside the candle body.
- **Target beyond the first barrier** with breathing room.

## Evidence That Would Invalidate This Analysis

- entry equals stop or target (undefined trade)
- stop inside immediate support/resistance (will be tagged by noise)
- target closer than stop (negative asymmetry)

## Output structure

1. `Summary` — coherent / rework
2. `Structure` — entry, stop, target, R-multiple
3. `Stop check` — vs support/resistance
4. `Target check` — vs barrier
5. `Caveats` — technical anchors used, freshness

## Best practices

- separate structure quality from thesis quality
- if R < 1, say rework before `propose_trade`
- anchor to technical levels, disclose when borrowed

## Usage examples

- "Use `risk-reward-sanity-check` on a long with entry 198.60, stop 189.30, target 210.50."
- "Use `risk-reward-sanity-check` on my gold plan before staging."
