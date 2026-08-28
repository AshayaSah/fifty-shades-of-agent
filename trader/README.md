# Exness MCP Trader

A simple MCP server for trading on the Exness MetaTrader 5 demo account. It exposes
trade tools that an AI agent (or any MCP client) can call.

## Requirements

- Windows with MetaTrader 5 terminal installed and **logged in**
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- Python 3.14

## Setup

1. Create a `.env` file from the template (copy `.env.example` to `.env`) and fill in your
   Exness demo credentials and database URL:

   ```
   EXNESS_LOGIN=12345678
   EXNESS_PASSWORD=your_password
   EXNESS_SERVER=Exness-MT5Trial5
   DATABASE_URL=postgresql://...
   ```

2. Install dependencies:

   ```bash
   uv sync
   ```

3. Open MetaTrader 5 and enable **Algo Trading** (the AutoTrading button in the toolbar);
   otherwise the broker will reject orders.

## Run the server

```bash
uv run python main.py
```

The server starts on `http://0.0.0.0:8000`. Connect your MCP client to:

```
http://localhost:8000/mcp
```

## Launch the MCP Inspector

Open a second terminal (keep the server running) and run:

```bash
uv run mcp dev python main.py
```

The Inspector loads your tools and lets you call them interactively. You can also point it
directly at the running HTTP server by entering `http://localhost:8000/mcp` as the server URL.

## Tools

| Tool | Purpose |
|------|---------|
| `ping` | Health check |
| `get_account_info` | Balance, equity, margin |
| `get_positions` | Open positions |
| `propose_trade` | Create a trade proposal |
| `get_proposal` | Fetch a proposal by ID |
| `resolve_symbol` | Convert "Apple"/"gold"/"EUR/USD" to the exact MT5 symbol |
| `get_safety_config` | Show current risk limits & kill switch state |
| `execute_trade` | Execute a pending proposal |
| `close_position` | Close an open position by ticket |
| `kill_switch` | Turn all trading off/on |

## Typical agent flow

1. `resolve_symbol("Apple")` -> `AAPLm`
2. `propose_trade("AAPLm", "buy", ...)` -> proposal `id`
3. `execute_trade(<id>, risk_percent)` -> status `executed`
4. `get_positions()` -> verify
5. `close_position(ticket)` -> close

## Safety guards

- `execute_trade` respects: kill switch, max 2% risk per trade, max 3 open positions,
  and a 15-minute proposal expiry.
- Proposals are stored in a PostgreSQL database (survive restarts).

## Tests

```bash
uv run pytest test_sizing.py test_symbol_resolve.py -q
```
