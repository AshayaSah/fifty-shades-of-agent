import MetaTrader5 as mt5
from mcp.server.mcpserver import MCPServer
import mt5_client
import proposals
import sizing

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


# TODO: Replace "PLACEHOLDER_TOKEN" with real TrueForge approval wiring in Phase 6.
PLACEHOLDER_TOKEN = "PLACEHOLDER_TOKEN"


@mcp.tool(structured_output=False)
def execute_trade(
    proposal_id: str,
    risk_percent: float,
    approval_token: str,
) -> dict:
    """Execute a pending trade proposal via MT5. Requires approval token."""
    if approval_token != PLACEHOLDER_TOKEN:
        return {"error": "Invalid approval token."}

    proposal = proposals.get_proposal(proposal_id)
    if proposal is None:
        return {"error": f"Proposal not found: {proposal_id}"}
    if proposal["status"] != "pending":
        return {"error": f"Proposal is not pending (status={proposal['status']})."}

    account = mt5_client.get_account_info()
    equity = account["equity"]
    spec = mt5_client.get_symbol_spec(proposal["symbol"])
    pip_value = spec["pip_value"]

    sl_distance = abs(proposal["entry"] - proposal["sl"])
    sl_distance_pips = sl_distance / spec["pip_size"]
    lot_size = sizing.calculate_lot_size(equity, risk_percent, sl_distance_pips, pip_value)
    if lot_size <= 0:
        proposals.update_proposal_status(proposal_id, "failed", {"reason": "Calculated lot size is 0"})
        return {"error": "Calculated lot size is 0. Check risk% and SL distance."}

    mt5_client.connect()
    order_type = mt5.ORDER_TYPE_BUY if proposal["direction"] == "buy" else mt5.ORDER_TYPE_SELL
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": proposal["symbol"],
        "volume": lot_size,
        "type": order_type,
        "price": mt5.symbol_info_tick(proposal["symbol"]).ask if order_type == mt5.ORDER_TYPE_BUY else mt5.symbol_info_tick(proposal["symbol"]).bid,
        "sl": proposal["sl"],
        "tp": proposal["tp"],
        "deviation": 20,
        "magic": 0,
        "comment": f"MCP:{proposal_id[:8]}",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    result = mt5.order_send(request)

    if result is None:
        code, comment = mt5.last_error()
        proposals.update_proposal_status(proposal_id, "failed", {"mt5_code": code, "mt5_comment": comment})
        return {"error": f"order_send failed: {comment} (code {code})"}

    if result.retcode != mt5.TRADE_RETCODE_DONE:
        proposals.update_proposal_status(proposal_id, "failed", {"mt5_code": result.retcode, "mt5_comment": result.comment})
        return {"error": f"Order rejected: {result.comment} (code {result.retcode})"}

    proposals.update_proposal_status(proposal_id, "executed", {
        "ticket": result.order,
        "lot_size": lot_size,
        "price": result.price,
    })
    return {
        "status": "executed",
        "ticket": result.order,
        "lot_size": lot_size,
        "price": result.price,
    }


if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8000)
