import MetaTrader5 as mt5
from datetime import datetime, timezone, timedelta
from mcp.server.mcpserver import MCPServer
import mt5_client
import proposals
import sizing
import audit
import db

db.init_db()

MAX_RISK_PERCENT = 2.0
MAX_CONCURRENT_POSITIONS = 3
PROPOSAL_EXPIRY_MINUTES = 15

_kill_switch_on = False

# TODO: Replace "PLACEHOLDER_TOKEN" with real TrueForge approval wiring in Phase 6.
PLACEHOLDER_TOKEN = "PLACEHOLDER_TOKEN"

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
    proposal = proposals.create_proposal(symbol, direction, entry, sl, tp, rationale)
    audit.log_event("proposal_created", {"proposal_id": proposal["id"], "symbol": symbol, "direction": direction})
    return proposal


@mcp.tool(structured_output=False)
def get_proposal(proposal_id: str) -> dict:
    """Get a trade proposal by its ID."""
    proposal = proposals.get_proposal(proposal_id)
    if proposal is None:
        return {"error": f"Proposal not found: {proposal_id}"}
    return proposal


@mcp.tool(structured_output=False)
def kill_switch(state: str) -> dict:
    """Set the kill switch 'on' or 'off'. Returns current state."""
    global _kill_switch_on
    if state not in ("on", "off"):
        return {"error": f"state must be 'on' or 'off', got '{state}'", "kill_switch": "on" if _kill_switch_on else "off"}
    _kill_switch_on = state == "on"
    audit.log_event("kill_switch", {"state": state})
    return {"kill_switch": state}

@mcp.tool(structured_output=False)
def execute_trade(
    proposal_id: str,
    risk_percent: float,
    approval_token: str,
) -> dict:
    """Execute a pending trade proposal via MT5. Requires approval token."""
    try:
        return _execute_trade(proposal_id, risk_percent, approval_token)
    except Exception as exc:
        audit.log_event(
            "trade_failed",
            {"proposal_id": proposal_id, "reason": "exception", "error": str(exc)},
        )
        return {"error": f"execute_trade failed: {exc}"}


def _execute_trade(proposal_id: str, risk_percent: float, approval_token: str) -> dict:
    if approval_token != PLACEHOLDER_TOKEN:
        audit.log_event("trade_rejected", {"proposal_id": proposal_id, "reason": "invalid_approval_token"})
        return {"error": "Invalid approval token."}

    if _kill_switch_on:
        audit.log_event("trade_rejected", {"proposal_id": proposal_id, "reason": "kill_switch_on"})
        return {"error": "Kill switch is ON. All trading is halted."}

    if risk_percent > MAX_RISK_PERCENT:
        audit.log_event("trade_rejected", {"proposal_id": proposal_id, "reason": "risk_exceeds_max", "risk_requested": risk_percent})
        return {"error": f"Risk {risk_percent}% exceeds maximum {MAX_RISK_PERCENT}%."}

    proposal = proposals.get_proposal(proposal_id)
    if proposal is None:
        return {"error": f"Proposal not found: {proposal_id}"}
    if proposal["status"] != "pending":
        return {"error": f"Proposal is not pending (status={proposal['status']})."}

    created = datetime.fromisoformat(proposal["created_at"])
    age_minutes = (datetime.now(timezone.utc) - created).total_seconds() / 60
    if age_minutes > PROPOSAL_EXPIRY_MINUTES:
        proposals.update_proposal_status(proposal_id, "expired")
        audit.log_event("trade_rejected", {"proposal_id": proposal_id, "reason": "proposal_expired", "age_minutes": round(age_minutes, 1)})
        return {"error": f"Proposal expired ({round(age_minutes, 1)} min old, max {PROPOSAL_EXPIRY_MINUTES})."}

    positions = mt5_client.get_positions()
    if len(positions) >= MAX_CONCURRENT_POSITIONS:
        audit.log_event("trade_rejected", {"proposal_id": proposal_id, "reason": "max_positions_reached", "open_count": len(positions)})
        return {"error": f"Max concurrent positions ({MAX_CONCURRENT_POSITIONS}) reached. Close a position first."}

    account = mt5_client.get_account_info()
    equity = account["equity"]
    spec = mt5_client.get_symbol_spec(proposal["symbol"])
    pip_value = spec["pip_value"]

    sl_distance = abs(proposal["entry"] - proposal["sl"])
    sl_distance_pips = sl_distance / spec["pip_size"]
    lot_size = sizing.calculate_lot_size(equity, risk_percent, sl_distance_pips, pip_value)
    if lot_size <= 0:
        proposals.update_proposal_status(proposal_id, "failed", {"reason": "lot_size_zero"})
        audit.log_event("trade_rejected", {"proposal_id": proposal_id, "reason": "lot_size_zero"})
        return {"error": "Calculated lot size is 0. Check risk% and SL distance."}

    mt5_client.connect()
    order_type = mt5.ORDER_TYPE_BUY if proposal["direction"] == "buy" else mt5.ORDER_TYPE_SELL
    tick = mt5.symbol_info_tick(proposal["symbol"])
    if tick is None:
        return {"error": f"No tick data for symbol {proposal['symbol']}."}
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": proposal["symbol"],
        "volume": lot_size,
        "type": order_type,
        "price": tick.ask if order_type == mt5.ORDER_TYPE_BUY else tick.bid,
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
        audit.log_event("trade_failed", {"proposal_id": proposal_id, "mt5_code": code, "mt5_comment": comment})
        return {"error": f"order_send failed: {comment} (code {code})"}

    if result.retcode != mt5.TRADE_RETCODE_DONE:
        proposals.update_proposal_status(proposal_id, "failed", {"mt5_code": result.retcode, "mt5_comment": result.comment})
        audit.log_event("trade_failed", {"proposal_id": proposal_id, "mt5_code": result.retcode, "mt5_comment": result.comment})
        return {"error": f"Order rejected: {result.comment} (code {result.retcode})"}

    proposals.update_proposal_status(proposal_id, "executed", {
        "ticket": result.order,
        "lot_size": lot_size,
        "price": result.price,
    })
    audit.log_event("trade_executed", {"proposal_id": proposal_id, "ticket": result.order, "lot_size": lot_size, "price": result.price})
    return {
        "status": "executed",
        "ticket": result.order,
        "lot_size": lot_size,
        "price": result.price,
    }


@mcp.tool(structured_output=False)
def close_position(ticket: int) -> dict:
    """Close an open position by its MT5 ticket."""
    try:
        return _close_position(ticket)
    except Exception as exc:
        audit.log_event("close_failed", {"ticket": ticket, "reason": "exception", "error": str(exc)})
        return {"error": f"close_position failed: {exc}"}


def _close_position(ticket: int) -> dict:
    if _kill_switch_on:
        audit.log_event("close_rejected", {"ticket": ticket, "reason": "kill_switch_on"})
        return {"error": "Kill switch is ON. All trading is halted."}

    mt5_client.connect()
    pos = mt5.positions_get(ticket=ticket)
    if not pos:
        return {"error": f"Position not found for ticket {ticket}"}
    position = pos[0]

    order_type = mt5.ORDER_TYPE_SELL if position.type == mt5.POSITION_TYPE_BUY else mt5.ORDER_TYPE_BUY
    tick = mt5.symbol_info_tick(position.symbol)
    if tick is None:
        return {"error": f"No tick data for symbol {position.symbol}."}
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": position.symbol,
        "volume": position.volume,
        "type": order_type,
        "position": ticket,
        "price": tick.bid if order_type == mt5.ORDER_TYPE_SELL else tick.ask,
        "deviation": 20,
        "magic": 0,
        "comment": f"MCP-CLOSE:{ticket}",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    result = mt5.order_send(request)

    if result is None:
        code, comment = mt5.last_error()
        audit.log_event("close_failed", {"ticket": ticket, "mt5_code": code, "mt5_comment": comment})
        return {"error": f"close failed: {comment} (code {code})"}

    if result.retcode != mt5.TRADE_RETCODE_DONE:
        audit.log_event("close_failed", {"ticket": ticket, "mt5_code": result.retcode, "mt5_comment": result.comment})
        return {"error": f"Close rejected: {result.comment} (code {result.retcode})"}

    audit.log_event("close_executed", {"ticket": ticket})
    return {
        "status": "closed",
        "ticket": ticket,
        "close_price": result.price,
    }


if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8000)
