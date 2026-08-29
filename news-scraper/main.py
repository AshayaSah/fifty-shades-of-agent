import uvicorn
from fastapi import FastAPI

from news_scraper.server import mcp

# FastMCP server exposed as an ASGI app over Streamable HTTP
mcp_app = mcp.http_app(path="/")

# Mount the MCP server inside FastAPI (FastMCP <-> FastAPI integration guide)
app = FastAPI(title="news-scraper", lifespan=mcp_app.lifespan)
app.mount("/mcp", mcp_app)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)