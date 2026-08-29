import os

import uvicorn
from fastapi import FastAPI

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


@app.get("/health")
def health() -> dict:
    """Liveness probe for the platform (Render health check)."""
    return {"status": "ok"}


app.mount("/", mcp_app)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))