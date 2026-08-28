# Trade Context

A compact, portable object skills pass between each other instead of raw chat
history. Keep it small and explicit. Skills read the fields they need and add
their own section.

```markdown
## Trade Context

### Identity
- symbol: AAPL
- resolved_symbol: AAPLm        # from trader.resolve_symbol
- direction: buy
- timeframe: 1d / swing
- source_freshness: { news: "2026-08-28", technical: "2026-08-28" }

### User thesis (from the user, not providers)
- core_claim: "..."
- invalidation: "..."
- evidence: [...]
- assumptions: [...]

### News layer (news-scraper)
- average_sentiment: 0.22
- sentiment_trend: improving | flat | deteriorating
- key_events: [earnings 2026-09-02, regulator probe]
- provider: news-scraper (FinBERT, BBC+NewsAPI)

### Technical layer (technical-analyst)
- verdict: bullish
- confidence: medium
- reasons: [...]
- support: 192.40
- resistance: 205.10
- suggested_stop_loss: 189.30
- suggested_take_profit: 210.50
- verdict_stable: yes | flipped
- provider: technical-analyst (yfinance)

### Structure
- entry: 198.60
- stop: 189.30
- target: 210.50
- r_multiple: 1.3

### Risk / execution (trader)
- account_equity: 10000
- risk_percent: 1.0
- max_risk_percent: 2.0
- concurrent_positions: 1 / 3
- proposal_id: ...
- kill_switch: off

### Decision
- readiness: ready | not_ready | rework
- open_items: [...]
```

## Rules

- Never overwrite a user-supplied field with a provider value without labelling
  the source.
- If a layer was not checked, write `not_checked` rather than guessing.
- Skills append their verdict under `### Decision` or their own section; they do
  not delete upstream context.
