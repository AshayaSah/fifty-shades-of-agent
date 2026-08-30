import os

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from news_scraper.server import mcp

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
app = FastAPI(title="news-scraper", lifespan=mcp_app.lifespan)

# MCP_API_TOKEN = os.environ.get("MCP_API_TOKEN", "")
#
#
# class APIKeyMiddleware(BaseHTTPMiddleware):
#     async def dispatch(self, request: Request, call_next):
#         if request.url.path == "/mcp" and MCP_API_TOKEN:
#             token = request.headers.get("x-api-key")
#             if not token:
#                 auth = request.headers.get("authorization", "")
#                 if auth.lower().startswith("bearer "):
#                     token = auth[7:].strip()
#             if token != MCP_API_TOKEN:
#                 return JSONResponse(
#                     status_code=401,
#                     content={"detail": "Invalid or missing API token"},
#                 )
#         return await call_next(request)
#
#
# app.add_middleware(APIKeyMiddleware)

ROOT_HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>news-scraper — MCP server</title>
<style>
  body { font-family: system-ui, sans-serif; max-width: 46rem; margin: 4rem auto; padding: 0 1rem; line-height: 1.6; color: #111; }
  code { background: #f1f1f1; padding: 2px 6px; border-radius: 4px; }
  ul { padding-left: 1.2rem; }
  .badge { display: inline-block; padding: 2px 8px; border-radius: 99px; background: #e6f4ea; color: #137333; font-size: .8rem; }
</style>
</head>
<body>
  <h1>news-scraper <span class="badge">MCP · Streamable HTTP</span></h1>
  <p>The <strong>news-intelligence layer</strong> of Fifty Shades of Agent. Scrapes company
  news from BBC RSS and NewsAPI, scores financial sentiment with FinBERT,
  extracts entities with spaCy, classifies event types, and persists everything
  to Postgres.</p>
  <h2>Tools</h2>
  <ul>
    <li><code>scrape_news</code> — fetch the latest headlines for a symbol</li>
    <li><code>get_news</code> — news persisted for a symbol</li>
    <li><code>get_sentiment_summary</code> — aggregate FinBERT/VADER sentiment</li>
    <li><code>get_sentiment_trend</code> — sentiment over time</li>
    <li><code>get_source_comparison</code> — coverage across sources</li>
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