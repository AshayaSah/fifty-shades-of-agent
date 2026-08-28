import pandas as pd


def find_support_resistance(df: pd.DataFrame, window: int = 10) -> dict:
    """Simple rolling swing-high/low support & resistance. `df` needs at
    least `window * 5` rows for a meaningful result; falls back to the
    full available range if shorter."""
    lookback = min(len(df), window * 5)
    recent = df.tail(lookback)

    resistance = recent["high"].rolling(window, min_periods=1).max().iloc[-1]
    support = recent["low"].rolling(window, min_periods=1).min().iloc[-1]

    return {"support": float(support), "resistance": float(resistance)}
