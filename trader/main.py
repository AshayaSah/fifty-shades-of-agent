from mcp.server.mcpserver import MCPServer
import mt5_client
import proposals

mcp = MCPServer("exness-mcp-trader")


@mcp.tool(structured_output=False)
def ping() -> dict:
    """Ping the server to check if it is alive."""
    return {"status": "ok"}


@mcp.tool(structured_output=False)
def get_account_info() -> dict:
    """Get MT5 account info: balance, equity, margin, and leverage."""
    return mt5_client.get_account_info()


@mcp.tool(structured_output=False)
def get_positions() -> list[dict]:
    """Get all open positions: ticket, symbol, volume, prices, profit, type."""
    return mt5_client.get_positions()


@mcp.tool(structured_output=False)
def propose_trade(
    symbol: str,
    direction: str,
    entry: float,
    sl: float,
    tp: float,
    rationale: str,
) -> dict:
    """Create a trade proposal. direction must be 'buy' or 'sell'."""
    if direction not in ("buy", "sell"):
        return {"error": f"direction must be 'buy' or 'sell', got '{direction}'"}
    return proposals.create_proposal(symbol, direction, entry, sl, tp, rationale)


@mcp.tool(structured_output=False)
def get_proposal(proposal_id: str) -> dict:
    """Get a trade proposal by its ID."""
    proposal = proposals.get_proposal(proposal_id)
    if proposal is None:
        return {"error": f"Proposal not found: {proposal_id}"}
    return proposal


if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8000)
