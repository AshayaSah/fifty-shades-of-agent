---
name: post-trade-debrief
description: Orchestrate a disciplined post-trade workflow for the fifty-shades-of-agent portfolio by reconstructing the original plan, reviewing execution and rule adherence via MT5 position history, and deciding whether the lesson is trade-specific or part of a repeatable pattern.
---

# Post-Trade Debrief

Use this skill after a trade closes (or is killed/expired) and the user wants one
learning workflow instead of manual review.

## Role

Act like a blunt, kind post-mortem reviewer. No hindsight theater: judge the
process against the plan that existed *before* the outcome was known.

## When to use it

Use it when the user wants to:

- learn from a closed or expired MT5 position
- tell whether a mistake was one-off or a pattern
- improve the next `pre-trade-check` input

## Inputs and context

Ask for:

- the ticket or symbol of the closed trade
- the original Trade Context / plan if they kept one
- what actually happened (or let the skill pull the position state)

Use the user's materials first.

## If critical data is missing

If the user supplies the plan and outcome, do not fetch.

Otherwise pull:

- `trader.get_positions()` (if still open) or ask the user for the closed ticket
- `news-scraper.get_sentiment_summary` + `get_sentiment_trend` around the hold
  period for context
- `technical-analyst.get_analysis_history` to see the verdict path the trade rode

## Analysis process

1. **Reconstruct the plan.** What was the thesis, entry, SL, target, and
   invalidation decided at `propose_trade` time?
2. **Execution review.** Did the fill/exit match the plan? Was `execute_trade`
   risk within `max_risk_percent`? Did expiry or kill switch interfere?
3. **Adherence.** Did the user follow their own rule, or override it? Note
   overrides explicitly.
4. **Outcome framing.** Separate luck from process. A winning trade with broken
   process is still a process failure; a losing trade with clean process is
   acceptable.
5. **Lesson type.** Trade-specific (one-off) or repeatable (pattern across
   journal)? Suggest a concrete change to `pre-trade-check` or `position-management`.

## Core Assessment Framework

- **Plan quality**: was there a written invalidation before entry?
- **Process adherence**: did action match plan?
- **Review honesty**: no rewriting the thesis after the fact.

## Evidence That Would Invalidate This Analysis

- no original plan exists and the user cannot recall one (then label it
  "unplanned" and flag the process gap)
- position record unavailable and user memory unreliable

## Output structure

1. `Summary` — lesson type (trade-specific / pattern)
2. `Original plan` — thesis, entry, SL, target
3. `Execution` — what happened vs plan
4. `Adherence` — followed or overridden
5. `Lesson` — one actionable change
6. `Caveats` — what data was reconstructed vs recalled

## Best practices

- never grade the trade by P&L alone
- if the plan was never written, the lesson is "write the plan"
- keep the lesson portable to the next skill run

## Usage examples

- "Use `post-trade-debrief` on ticket 123456 and tell me the real lesson."
- "Use `post-trade-debrief` on my expired AAPL proposal."
