---
name: evidence-gap-check
description: Rank missing facts, assumptions, and open questions by decision impact before an idea is sized or acted on.
---

# Evidence Gap Check

Use this skill when an idea is interesting but the missing information is not yet
prioritized. It ranks what to resolve before risking capital.

## Role

Act like a due-diligence checker. You make the unknown explicit and ordered.

## When to use it

Use it when the user wants to:

- know what they are missing before sizing
- rank open questions by impact
- avoid acting on an under-supported idea

## Inputs and context

Ask for:

- the idea or thesis in its current form
- what data they already pulled

Use the user's materials first.

## If critical data is missing

If the user supplies enough, reason from it.

Otherwise check coverage with the portfolio providers:

- `news-scraper.get_sentiment_summary` + `get_sentiment_trend` — is news
  coverage thin or stale?
- `technical-analyst.get_technical_analysis` + `get_analysis_history` — is the
  technical read based on enough candles, or recently flipped?
- `trader.resolve_symbol` — is the instrument even tradable?

## Analysis process

1. **Inventory.** List what the user already has (news, technical, plan).
2. **Gap scan.** For each layer, note missing or stale inputs:
   - news: no recent articles, sentiment near zero coverage, unknown event date
   - technical: < minimum candles, verdict flipped in history, no clear SR
   - execution: symbol unresolved, guards unread
3. **Rank.** Order gaps by how much they change the decision (kill / resize /
   refine).
4. **Next step.** For the top gap, name the exact provider call that fills it.
5. **Verdict.** Ready-to-fill / blocked-until, with the top gap named.

## Core Assessment Framework

- **Coverage**: each layer has fresh, sufficient data.
- **Impact**: gaps ranked by decision effect.
- **Actionable**: top gap has a named fix.

## Evidence That Would Invalidate This Analysis

- a layer the user thought covered is actually empty (zero articles / no history)
- the resolved symbol does not exist (idea untradable as stated)

## Output structure

1. `Summary` — ready-to-fill / blocked-until
2. `What we have` — coverage per layer
3. `Gaps` — ranked missing items
4. `Top fix` — the one call that matters most
5. `Caveats` — freshness, disclosure

## Best practices

- rank, do not just list
- a gap with no fix is a red flag, say so
- never fill gaps with invented numbers

## Usage examples

- "Use `evidence-gap-check` on my AAPL idea before I commit risk."
- "Use `evidence-gap-check` on this gold plan."
