def calculate_lot_size(
    equity: float,
    risk_percent: float,
    sl_distance_pips: float,
    pip_value: float,
) -> float:
    """Calculate lot size based on equity, risk %, SL distance, and pip value.

    pip_value is the account-currency value of 1 pip for 1 standard lot.
    """
    if sl_distance_pips <= 0 or pip_value <= 0:
        return 0.0
    risk_amount = equity * risk_percent / 100
    lot_size = risk_amount / (sl_distance_pips * pip_value)
    return round(lot_size, 2)
