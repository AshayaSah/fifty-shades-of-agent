from mcp.server.mcpserver import MCPServer

mcp = MCPServer("exness-mcp-trader")


@mcp.tool()
def ping() -> dict:
    """Ping the server to check if it is alive."""
    return {"status": "ok"}


if __name__ == "__main__":
    mcp.run(transport="stdio")
