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
│   └── Dockerfile         # multi-stage uv build (dev / prod)
├── technical-analyst/     # price data + technical analysis (MCP)
│   └── Dockerfile         # multi-stage uv build (dev / prod)
├── trader/                # Exness MT5 order execution (MCP)
│   └── Dockerfile         # multi-stage uv build (dev / prod)
├── docker-compose.yml     # development environment (with local Postgres)
├── docker-compose.prod.yml# production environment (bring-your-own DB)
└── README.md              # this overview
```

Each subfolder has its own `Dockerfile` and `README.md` with setup, tools, and
configuration details.

## Running locally (without Docker)

Each service is a separate `uv` project. From the repo root:

```sh
uv run --project news-scraper python news-scraper/main.py
uv run --project technical-analyst python technical-analyst/main.py
uv run --project trader python trader/main.py
```

Or run all three with a process manager, as the root `Procfile` does
(`foreman start` / `overmind start`).

## Running with Docker

Each service has its own multi-stage `Dockerfile` built around
[`uv`](https://docs.astral.sh/uv/). Every Dockerfile produces both a
**development** and a **production** image, selected with `--target`, so the
`news-scraper` Dockerfile (which bundles the spaCy model) stays separate from
the leaner `technical-analyst` and `trader` ones.

### Building an image directly

Each image is built from within its own service directory:

```sh
# Development (includes pytest, editable installs)
docker build --target dev -t fifty/news-scraper:dev ./news-scraper

# Production (runtime-only, non-root user, no source mount)
docker build --target prod -t fifty/technical-analyst:prod ./technical-analyst
```

### Development environment — `docker-compose.yml`

Boots all three services plus a local Postgres, mounts source as a volume for
hot-reload, and configures each service to use the local database:

```sh
cp news-scraper/.env.example news-scraper/.env   # fill in keys as needed
cp technical-analyst/.env.example technical-analyst/.env
cp trader/.env.example trader/.env

docker compose up --build
```

Host ports are mapped so services don't clash:

| Service            | Container port | Host port |
| ------------------ | -------------- | --------- |
| `db` (Postgres)    | 5432           | 5432      |
| `news-scraper`     | 8000           | 8001      |
| `technical-analyst`| 8000           | 8002      |
| `trader`           | 8000           | 8003      |
| `mt5-sidecar` (RPyC)| 18812         | 18812     |
| `mt5-sidecar` (noVNC)| 8080         | 8080      |

Run a single service with `docker compose up --build <service>`, and tear
everything down (including the DB volume) with `docker compose down -v`.

> **Note:** local Postgres is a convenience for development. In production the
> services talk to your Neon instance, so no database container is included.

### Production environment — `docker-compose.prod.yml`

Same set of per-service Dockerfiles, but the `prod` **target**: no source
volumes, restart policies, and a bring-your-own database. Set the required
values in a `.env.prod` file (derived from each service's `.env.example`):

```sh
# .env.prod
NEWS_DATABASE_URL=postgresql://user:pass@host/db
ANALYST_DATABASE_URL=postgresql://user:pass@host/db?sslmode=require
TRADER_DATABASE_URL=postgresql://user:pass@host/db
TWELVE_DATA_API_KEY=...
EXNESS_LOGIN=...
EXNESS_PASSWORD=...
EXNESS_SERVER=...
VNC_PASSWORD=...        # noVNC password for the MT5 sidecar
```

Then deploy:

```sh
docker compose -f docker-compose.prod.yml --env-file .env.prod up --build -d
```

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
  build time (downloaded in the `base` stage of `news-scraper/Dockerfile`). The
  large PyTorch/transformers FinBERT model is fetched lazily on first sentiment
  call, which makes the first image build and first scrape slower.
- **Secrets are never baked into images** — everything comes from `env_file` /
  environment variables at runtime.

## Deploying to Render / Vercel

- **`render.json`** (Render Blueprint) defines all three MCP servers as Docker
  web services. Note that Render **cannot host the Wine + MetaTrader 5
  sidecar**, so the `trader` service boots and exposes its MCP tools but live
  order execution requires you to point `MT5_HOST`/`MT5_PORT` at an externally
  hosted `mt5-sidecar` (or run the sidecar elsewhere).
- **`vercel.json`** is a status-only deployment. Vercel is designed for
  serverless functions and static sites, which cannot host these long-lived,
  persistent `streamable-http` MCP servers. `api/news_scraper.py`,
  `api/technical_analyst.py`, and `api/trader.py` expose minimal serverless
  status/health handlers with a `501` note. To serve the real MCP endpoints,
  deploy with Render or Docker Compose instead.
