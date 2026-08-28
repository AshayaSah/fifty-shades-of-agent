# Fifty Shades of Agent

A trading-agent hackathon project built from three standalone MCP (Model Context
Protocol) servers that work together to research, analyze, and trade financial
markets.

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

## How they fit together

Each service is independent and communicates over MCP. A coordinating agent can
chain them — e.g. ask `news-scraper` for sentiment on a ticker, `technical-analyst`
for a technical verdict, then route a go/no-go decision into `trader` to place the
trade — while every layer persists its own state to its own database.

## Repo layout

```
fifty-shades-of-agent/
├── news-scraper/          # news + sentiment + entities (MCP, streamable-http)
├── technical-analyst/     # price data + technical analysis (MCP)
├── trader/                # Exness MT5 order execution (MCP)
└── README.md              # this overview
```

Each subfolder has its own `README.md` with setup, tools, and configuration details.
