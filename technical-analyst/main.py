import uvicorn
from fastapi import FastAPI

from technical_analyst.config import settings
from technical_analyst.server import mcp

# Mirror the DNS-rebinding protection the old SDK transport_security provided
allowed_hosts = [h.strip() for h in settings.mcp_allowed_hosts.split(",") if h.strip()]

# FastMCP server exposed as an ASGI app over Streamable HTTP
mcp_app = mcp.http_app(
    path="/",
    host_origin_protection=bool(allowed_hosts),
    allowed_hosts=allowed_hosts,
)

# Mount the MCP server inside FastAPI (FastMCP <-> FastAPI integration guide)
app = FastAPI(title="technical-analyst", lifespan=mcp_app.lifespan)
app.mount("/mcp", mcp_app)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)