import os

import uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from technical_analyst.server import mcp

# FastMCP server exposed as an ASGI app over the Streamable HTTP transport,
# using JSON-only responses in stateless mode (no SSE / text-event-stream).
# Stateless HTTP is proxy-friendly (Render) and drops the GET stream entirely,
# so clients talk to the endpoint with plain JSON-RPC POSTs.
mcp_app = mcp.http_app(
    path="/mcp",
    transport="streamable-http",
    stateless_http=True,
    json_response=True,
)

# Mount the MCP server at the app root so it is reachable at exactly /mcp
# (no trailing slash). FastAPI's own routes (/health, /docs, /openapi.json)
# are registered before the mount and therefore take precedence.
app = FastAPI(title="technical-analyst", lifespan=mcp_app.lifespan)

ROOT_HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>technical-analyst — MCP server</title>
<style>
  body { font-family: system-ui, sans-serif; max-width: 46rem; margin: 4rem auto; padding: 0 1rem; line-height: 1.6; color: #111; }
  code { background: #f1f1f1; padding: 2px 6px; border-radius: 4px; }
  ul { padding-left: 1.2rem; }
  .badge { display: inline-block; padding: 2px 8px; border-radius: 99px; background: #e6f4ea; color: #137333; font-size: .8rem; }
</style>
</head>
<body>
  <h1>technical-analyst <span class="badge">MCP · Streamable HTTP</span></h1>
  <p>The <strong>technical-analysis layer</strong> of Fifty Shades of Agent. Fetches price
  data (yfinance primary, Twelve Data fallback) and produces a full technical
  report — trend, momentum, volatility, and volume indicators, support/resistance
  levels, and a bullish/bearish/neutral verdict with suggested stop-loss and
  take-profit. Reports are saved to Neon for later recall.</p>
  <h2>Tools</h2>
  <ul>
    <li><code>get_price_data</code> — candle history for a symbol</li>
    <li><code>get_technical_analysis</code> — indicators + verdict + levels</li>
    <li><code>get_analysis_history</code> — past reports stored on Neon</li>
    <li><code>ping</code> — liveness for MCP clients</li>
  </ul>
  <h2>Endpoint</h2>
  <p>Interact via JSON-RPC: <code>POST /mcp</code> <span class="badge" style="background:#fef7e0;color:#b06000">200 OK</span></p>
  <p><a href="/mcp">/mcp</a> · <a href="/health">/health</a> · <a href="/docs">/docs</a></p>
</body>
</html>"""


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    """Landing page describing the service."""
    return ROOT_HTML


@app.get("/health")
def health() -> dict:
    """Liveness probe for the platform (Render health check)."""
    return {"status": "ok"}


app.mount("/", mcp_app)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))