"""Vercel serverless handler for the news-scraper MCP server.

WARNING: Vercel runs short-lived, stateless serverless functions. The MCP
`streamable-http` transport needs a persistent HTTP session and a long-lived
process, so live MCP calls must NOT be served from Vercel. This endpoint only
reports service name/version and returns a 501 for anything else.

Run the real server with Docker Compose, Render, or `uv run main.py` instead.
"""
from http import HTTPStatus


def handler(request=None):
    return {
        "service": "news-scraper",
        "status": "ok",
        "note": "Live MCP streamable-http is not available on Vercel. "
                "Deploy with Docker/Render or run `uv run main.py`.",
        "health": "/mcp/",
    }, HTTPStatus.OK
