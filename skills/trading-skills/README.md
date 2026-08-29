# Trading Skills — fifty-shades-of-agent portfolio

Agent skills for the **fifty-shades-of-agent** trading system. The format follows
[`marian2js/trading-skills`](https://github.com/marian2js/trading-skills): each
skill is a `SKILL.md` with `name` + `description` frontmatter, a conservative
analyst role, an explicit analysis process, and a fixed output structure.

Unlike the generic upstream repo, these skills are **wired to this portfolio's
three MCP servers**:

| Server | Role in skills |
| --- | --- |
| `news-scraper` | sentiment, entities, event classification (FinBERT) |
| `technical-analyst` | trend/momentum/volatility verdict + SL/TP anchors |
| `trader` (Exness MT5) | symbol resolve, propose/execute, positions, safety guards |

Skills carry a compact **Trade Context** (see `references/trade-context.md`)
between runs instead of raw transcript, and they never bypass the trader
server's hard guards (`max_risk_percent` 2.0, `max_concurrent_positions` 3,
15-minute proposal expiry, kill switch).

## Start here

- One go / no-go verdict for a trade idea: `pre-trade-check`
- Whole-book risk before adding exposure: `portfolio-risk-review`
- Managing an open position: `position-management`
- Learning from a closed trade: `post-trade-debrief`
- Verifying a plan is executable: `execution-plan-check`
- Sizing the trade: `position-sizing`
- Testing entry/stop/target shape: `risk-reward-sanity-check`
- Pressure-testing the claim: `thesis-validation`
- Finding missing info: `evidence-gap-check`
- Triaging a list of names: `watchlist-review`

## Reference docs

- `references/portfolio-data-providers.md` — full tool inventory for the three MCP servers
- `references/trade-context.md` — the portable context object skills share

## Available skills

| Skill | Summary | Group |
| --- | --- | --- |
| `pre-trade-check` | Route a trade idea through news + technical + MT5 guards for a ready/not-ready verdict. | workflows |
| `portfolio-risk-review` | Whole-book concentration, correlation, catalyst clustering, and live fragility. | workflows |
| `position-management` | Hold / trim / tighten / exit decision on an open MT5 position. | workflows |
| `post-trade-debrief` | Reconstruct plan, review adherence, extract a portable lesson. | workflows |
| `execution-plan-check` | Pre-flight a plan against symbol resolve, guards, expiry, capacity. | trade-construction |
| `position-sizing` | Conservative `risk_percent` within the server's max-risk guard. | trade-construction |
| `risk-reward-sanity-check` | Coherence and asymmetry of entry/stop/target before staging. | trade-construction |
| `thesis-validation` | Core claim, evidence, invalidation, dependencies before structure. | thesis-validation |
| `evidence-gap-check` | Rank missing facts/assumptions by decision impact. | thesis-validation |
| `watchlist-review` | Rank watchlist names by setup quality, tradability, redundancy. | idea-discovery |

## Trust model

Every skill discloses what came from the user versus a provider, the data
freshness, and what is still missing. No skill promises an outcome, and no skill
calls `execute_trade` or `kill_switch` except on an explicit user instruction.
