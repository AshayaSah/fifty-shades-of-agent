from datetime import datetime

import pandas as pd
from pydantic import BaseModel


class Candle(BaseModel):
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int


class OHLCVSeries(BaseModel):
    symbol: str
    interval: str  # "1d" for now — other intervals may be added later
    candles: list[Candle]
    source: str  # which provider produced this ("yfinance" | "twelve_data")

    def to_dataframe(self) -> pd.DataFrame:
        df = pd.DataFrame([c.model_dump() for c in self.candles])
        if df.empty:
            return df
        df.set_index("timestamp", inplace=True)
        df.sort_index(inplace=True)
        return df
