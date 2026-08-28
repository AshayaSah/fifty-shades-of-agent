"""End-to-end demo against the live Exness demo account.

Requires the MT5 terminal to be running and logged in.
Run with:  uv run pytest test_e2e_demo.py -v -s
"""

import main

SYMBOL = "EURUSDm"
RISK_PERCENT = 1.0


def test_e2e_live_trade():
    print("\n===== Exness MCP Trader - Live E2E Demo =====")

    # 1. Propose a trade
    entry = 1.16
    sl = entry - 0.0010
    tp = entry + 0.0010
    prop = main.propose_trade(
        SYMBOL,
        "buy",
        entry,
        sl,
        tp,
        "E2E demo - safe 10-pip range trade",
    )
    assert "error" not in prop, f"propose_trade failed: {prop}"
    proposal_id = prop["id"]
    print(f"[1] Propose trade -> id={proposal_id} status={prop['status']}")

    # 2. Guards (approval token removed — safety guards still enforced)
    cfg = main.get_safety_config()
    print(f"[2] Safety config -> {cfg}")

    # 3. Execute the trade (no approval token)
    result = main.execute_trade(proposal_id, RISK_PERCENT)
    assert result.get("status") == "executed", f"execute_trade failed: {result}"
    ticket = result["ticket"]
    print(f"[3] Execute trade -> status={result['status']} ticket={ticket} lot={result['lot_size']}")

    # 4. Verify the position is present
    positions = main.get_positions()
    assert any(p["ticket"] == ticket for p in positions), "New position not found in get_positions"
    print(f"[4] Verify position -> open positions={len(positions)} (ticket {ticket} present)")

    # 5. Close the position
    close = main.close_position(ticket)
    assert close.get("status") == "closed", f"close_position failed: {close}"
    print(f"[5] Close position -> status={close['status']} price={close.get('close_price')}")

    # 6. Verify the position is gone
    positions_after = main.get_positions()
    assert not any(p["ticket"] == ticket for p in positions_after), "Position still present after close"
    print(f"[6] Verify close -> open positions={len(positions_after)} (ticket {ticket} gone)")

    print("===== E2E DEMO PASSED =====")
