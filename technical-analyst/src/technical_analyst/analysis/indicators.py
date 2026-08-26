import pandas as pd
import pandas_ta as ta

# Minimum candles needed for the slowest indicator (SMA-50) to produce a
# non-NaN value on the most recent row.
MIN_CANDLES_REQUIRED = 55


def add_core_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Adds trend, momentum, volatility, and volume indicators in place
    (on a copy) and returns the enriched dataframe. `df` must have
    lowercase open/high/low/close/volume columns (see OHLCVSeries.to_dataframe)."""
    df = df.copy()

    df["sma_20"] = ta.sma(df["close"], length=20)
    df["sma_50"] = ta.sma(df["close"], length=50)
    df["ema_20"] = ta.ema(df["close"], length=20)
    df["rsi_14"] = ta.rsi(df["close"], length=14)

    macd = ta.macd(df["close"])
    if macd is not None:
        df = pd.concat([df, macd], axis=1)

    bbands = ta.bbands(df["close"], length=20)
    if bbands is not None:
        df = pd.concat([df, bbands], axis=1)

    df["atr_14"] = ta.atr(df["high"], df["low"], df["close"], length=14)
    df["obv"] = ta.obv(df["close"], df["volume"])

    return df
