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
│   └── Dockerfile         # multi-stage uv build (dev / prod)
├── docker-compose.yml     # development environment (with local Postgres)
├── docker-compose.prod.yml# production environment (bring-your-own DB)
├── render.yaml            # Render Blueprint for news-scraper + technical-analyst
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
- **`news-scraper`** bundles the spaCy `en_core_web_sm` model into the image at
  build time (downloaded in the `base` stage of `news-scraper/Dockerfile`).
  PyTorch is pinned to **CPU-only wheels** (`torch~=2.13.0+cpu` via the
  `pytorch-cpu` uv index) so FinBERT runs fine on a single CPU instance without
  pulling gigabytes of CUDA/nvidia dependencies; the FinBERT model itself is
  fetched lazily on the first sentiment call.
- **Secrets are never baked into images** — everything comes from `env_file` /
  environment variables at runtime.

## Deploying to Render

Both HTTP-accessible MCP servers (`news-scraper`, `technical-analyst`) are defined
as Render **Docker web services** in the root **`render.yaml`** Blueprint. Each
builds its own multi-stage `Dockerfile` (Python 3.13 + uv) and exposes:

- `/mcp` — the Streamable-HTTP (JSON-only, stateless) MCP endpoint
- `/health` — liveness probe that Render uses for health checks

Note that Render **cannot host the Wine + MetaTrader 5 sidecar**, so `trader` is
not part of the Blueprint — live order execution still requires an externally
hosted `mt5-sidecar` (see the `trader/` docs).

### Blueprint (`render.yaml`)

```yaml
services:
  - name: news-scraper            # runtime: docker, dockerfilePath/context: news-scraper/
    envVars:
      - { key: DATABASE_URL, sync: false }   # set in the dashboard
      - { key: NEWSAPI_KEY,  sync: false }
      - { key: MCP_API_TOKEN, sync: false }
  - name: technical-analyst       # runtime: docker, dockerfilePath/context: technical-analyst/
    envVars:
      - { key: NEON_DATABASE_URL,    sync: false }
      - { key: TWELVE_DATA_API_KEY,  sync: false }
      - { key: MCP_API_TOKEN,        sync: false }
      - { key: CACHE_TTL_SECONDS, value: "300" }
      - { key: LOG_LEVEL,        value: INFO }
```

> **`MCP_API_TOKEN` guards `/mcp`.** When set, every request to `/mcp` must carry
> the token via `X-API-Key: <token>` or `Authorization: Bearer <token>`
> (unauthenticated requests get `401`). Leave it unset to disable auth locally
> (the pytest suite relies on this). `/` and `/health` stay public.

Secrets are declared with `sync: false` so they are **never** committed — set them
once in the Render dashboard (Dashboard → service → Environment).

### Via the dashboard (recommended)

1. Push the branch and open
   `https://dashboard.render.com` → **New +** → **Blueprint**, point it at this
   repo, and select `render.yaml`.
2. Fill in the `sync: false` env vars in each service's Environment tab.
3. Render builds the images and deploys both services.

### Via the Render CLI

The CLI can create the services directly (validating `render.yaml` first):

```sh
render blueprints validate render.yaml          # check the Blueprint parses

# news-scraper
render services create \
  --name news-scraper --type web_service --runtime docker \
  --repo https://github.com/AshayaSah/fifty-shades-of-agent \
  --branch refactor/fastapi-mcp-migrate \
  --root-directory news-scraper --plan free --region oregon \
  --health-check-path /health \
  --env-var 'DATABASE_URL=postgresql://…?sslmode=require&channel_binding=require' \
  --env-var 'NEWSAPI_KEY=…' \
  --env-var 'MCP_API_TOKEN=…' --output json

# technical-analyst
render services create \
  --name technical-analyst --type web_service --runtime docker \
  --repo https://github.com/AshayaSah/fifty-shades-of-agent \
  --branch refactor/fastapi-mcp-migrate \
  --root-directory technical-analyst --plan free --region oregon \
  --health-check-path /health \
  --env-var 'NEON_DATABASE_URL=postgresql://…?sslmode=require' \
  --env-var 'TWELVE_DATA_API_KEY=…' \
  --env-var 'MCP_API_TOKEN=…' \
  --env-var 'CACHE_TTL_SECONDS=300' --env-var 'LOG_LEVEL=INFO' --output json
```

> Quote env var values with **single quotes** — a database URL containing `&`
> splits into a background job when shell-sourced, silently emptying the value.

Existing services can be re-checked / redeployed:

```sh
render services                              # list + service IDs
render deploys create -s <service-id>        # redeploy the latest commit
render logs -r <service-id> --tail           # follow build + runtime logs
```

### Smoke-testing a live service

```sh
curl -s https://<service>.onrender.com/health                       # {"status":"ok"}
curl -s -X POST https://<service>.onrender.com/mcp -H "Accept: application/json" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $MCP_API_TOKEN" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"smoke","version":"0.1"}}}'
```

MCP clients such as Claude Desktop/Code can pass the token per server:

```json
{
  "mcpServers": {
    "news-scraper": {
      "url": "https://<service>.onrender.com/mcp",
      "headers": { "Authorization": "Bearer $MCP_API_TOKEN" }
    }
  }
}
```

### Custom domain

Attach your own domain (e.g. `*.saastralabs.com`) per service under
Dashboard → service → **Settings → Domains**, add the `CNAME` Render shows you,
and wait for the cert to issue. The MCP endpoints stay identical on the custom
host.
