# Fifty Shades of Agent

A trading-agent hackathon project built from three standalone MCP (Model Context
Protocol) servers that work together to research, analyze, and trade financial
markets, plus a Next.js dashboard that orchestrates them through a coordinating
agent and a set of reusable trading skills.

## Components

### 1. `news-scraper`
The news-intelligence layer. Scrapes company news from multiple sources (BBC RSS,
NewsAPI), scores financial sentiment with FinBERT, extracts entities with spaCy,
classifies event types, and persists everything to Postgres. Lets an agent
answer "what's happening with this company and is the sentiment positive?"

### 2. `technical-analyst`
The technical-analysis layer. Fetches price data (yfinance primary, Twelve Data
fallback) and produces a full technical report — trend, momentum, volatility, and
volume indicators, support/resistance levels, and a bullish/bearish/neutral verdict
with suggested stop-loss and take-profit. Reports are saved to Neon for later recall.

### 3. `trader`
The execution layer. Exposes an MCP server for trading on the Exness MetaTrader 5
demo account. It resolves human-friendly symbols ("Apple", "gold"), proposes
trades, enforces safety guards (kill switch, max risk, position cap, expiry), and
executes/closes positions on MT5.

### 4. `frontend` (dashboard)
A Next.js web dashboard that drives the whole system through a TrueForge
coordinating agent. It streams the agent's live work (reasoning, tool calls,
phases) to the browser as Server-Sent Events and persists exploration sessions.

### 5. `skills` (trading workflows)
A portfolio of agent skills (`SKILL.md` files) that encode conservative trading
workflows — pre-trade checks, risk review, position sizing, thesis validation —
wired directly to the three MCP servers above.

## How they fit together

Each service is independent and communicates over MCP. A coordinating agent can
chain them — e.g. ask `news-scraper` for sentiment on a ticker, `technical-analyst`
for a technical verdict, then route a go/no-go decision into `trader` to place the
trade — while every layer persists its own state to its own database. The `frontend`
dashboard orchestrates this chaining via the TrueForge agent and visualizes it live.

## Repo layout

```
fifty-shades-of-agent/
├── news-scraper/          # news + sentiment + entities (MCP, streamable-http)
├── technical-analyst/     # price data + technical analysis (MCP)
├── trader/                # Exness MT5 order execution (MCP)
├── frontend/              # Next.js dashboard + TrueForge orchestration
├── api/                   # Vercel status/health handlers (status-only)
├── skills/
│   └── trading-skills/    # SKILL.md trading workflow library
├── Procfile               # runs all three MCP servers via uv
└── README.md              # this overview
```

Each service subfolder has its own `README.md` with its folder-specific setup,
tools, and configuration details.

## Running locally

Each service is a separate `uv` project. From the repo root:

```sh
uv run --project news-scraper python news-scraper/main.py
uv run --project technical-analyst python technical-analyst/main.py
uv run --project trader python trader/main.py
```

Or run all three with a process manager, as the root `Procfile` does
(`foreman start` / `overmind start`).

The frontend is a separate Next.js app (run with `bun`). See `frontend/README.md`.

## Notes

- **`trader` runs on both Linux and Windows**.
  - **Linux**: uses the `mt5linux` bridge and connects over RPyC to a separate
    Wine + MetaTrader 5 sidecar (`mt5-sidecar`, the `lprett/mt5linux` image).
    The sidecar auto-logs into MT5 via `EXNESS_LOGIN`/`EXNESS_PASSWORD`/
    `EXNESS_SERVER`.
  - **Windows**: uses the native `metatrader5` package directly against the
    local MT5 terminal (no sidecar).
  - Dependency selection is automatic via platform markers in `pyproject.toml`
    (`mt5linux` on `linux`, `metatrader5` on `win32`), and `mt5_client.py`
    picks the backend at runtime.
- **`news-scraper`** bundles the spaCy `en_core_web_sm` model at build time and
  lazy-loads the large PyTorch/transformers FinBERT model on first sentiment
  call, which makes the first scrape slower.
- **Secrets are never baked into images** — everything comes from environment
  variables / `.env` files at runtime.
