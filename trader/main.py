from mcp.server.mcpserver import MCPServer
import mt5_client

mcp = MCPServer("exness-mcp-trader")


@mcp.tool()
def ping() -> dict:
    """Ping the server to check if it is alive."""
    return {"status": "ok"}


@mcp.tool()
def get_account_info() -> dict:
    """Get MT5 account info: balance, equity, margin, and leverage."""
    return mt5_client.get_account_info()


@mcp.tool()
def get_positions() -> list[dict]:
    """Get all open positions: ticket, symbol, volume, prices, profit, type."""
    return mt5_client.get_positions()


if __name__ == "__main__":
    mcp.run(transport="stdio")
