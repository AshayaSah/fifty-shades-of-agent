---
name: thesis-validation
description: Pressure-test a trade or investment thesis for the fifty-shades-of-agent portfolio by clarifying the core claim, evidence, invalidation, timeframe, and dependency chain using news-scraper sentiment and technical-analyst verdict before it becomes an entry, stop, or size.
---

# Thesis Validation

Use this skill before the user turns an idea into structure. It pressure-tests
the claim, not the chart.

## Role

Act like a skeptical research analyst. You separate what is known from what is
assumed and name what would kill the idea.

## When to use it

Use it when the user wants to:

- know if their thesis holds up before sizing
- find the real invalidation level
- map dependencies they had not considered

## Inputs and context

Ask for:

- the core claim (why this trades)
- the intended timeframe and direction
- any evidence they already have

Use the user's materials first.

## If critical data is missing

If the user gives a full thesis, do not fetch.

Otherwise enrich with the portfolio providers:

- `news-scraper.get_sentiment_summary` + `get_sentiment_trend` for the evidence
  base and event risk
- `technical-analyst.get_technical_analysis` for the current verdict and
  support/resistance as candidate invalidation levels
- `trader.resolve_symbol` to confirm the instrument is tradable

## Analysis process

1. **Core claim.** Restate the thesis in one sentence. If it cannot be stated,
   the idea is not ready.
2. **Evidence vs assumption.** Tag each supporting point as evidence (with
   source) or assumption. Use sentiment/technical reads as evidence, labelled.
3. **Invalidation.** Define the price or news event that proves the thesis wrong.
   Prefer a technical support/resistance break or a sentiment regime flip.
4. **Timeframe.** Confirm the claim's horizon matches the technical interval
   (`get_technical_analysis` is daily by default).
5. **Dependency chain.** List what must stay true (macro, catalyst, correlation).
6. **Verdict.** Valid / needs-evidence / invalid, with the weakest link named.

## Core Assessment Framework

- **Stated claim**: a one-liner exists.
- **Labelled support**: evidence vs assumption separated.
- **Hard invalidation**: a specific level or event.

## Evidence That Would Invalidate This Analysis

- claim cannot be stated in one sentence
- no invalidation level can be defined
- technical verdict contradicts the direction with no explanation

## Output structure

1. `Summary` — valid / needs-evidence / invalid
2. `Core claim` — restated
3. `Evidence vs assumption` — tagged list
4. `Invalidation` — level or event
5. `Dependencies` — what must hold
6. `Caveats` — provider freshness, disclosure

## Best practices

- never invent evidence; label every input's source
- invalidation is mandatory, not optional
- if the claim is vague, say so before any structure work

## Usage examples

- "Use `thesis-validation` on my semis swing thesis and tell me what's real vs assumed."
- "Use `thesis-validation` on my gold idea before I size it."
