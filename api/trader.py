"""Vercel serverless handler for the trader MCP server.

WARNING: Vercel runs short-lived, stateless serverless functions. The MCP
`streamable-http` transport needs a persistent HTTP session and a long-lived
process, so live MCP calls must NOT be served from Vercel. The `trader` also
depends on a MetalTrader 5 backend (native MT5 on Windows, or a Wine + MT5
sidecar on Linux), which Vercel cannot host. This endpoint only reports status.

Run the real server with Docker Compose, Render, or `uv run main.py` instead.
"""
from http import HTTPStatus


def handler(request=None):
    return {
        "service": "trader",
        "status": "ok",
        "note": "Live MCP streamable-http is not available on Vercel. "
                "Deploy with Docker/Render or run `uv run main.py`.",
        "health": "/mcp/",
    }, HTTPStatus.OK
