from datetime import datetime, timedelta, timezone

import pandas as pd
import yfinance as yf

from technical_analyst.data.models import Candle, OHLCVSeries
from technical_analyst.data.providers.base import DataProvider, ProviderError
from technical_analyst.data.providers.symbols import resolve_symbol
from technical_analyst.utils.logging import get_logger

logger = get_logger(__name__)

# yfinance interval strings we support for now.
_SUPPORTED_INTERVALS = {"1d"}


class YFinanceProvider(DataProvider):
    name = "yfinance"

    def fetch(self, symbol: str, interval: str = "1d", lookback_days: int = 90) -> OHLCVSeries:
        if interval not in _SUPPORTED_INTERVALS:
            raise ProviderError(f"yfinance provider does not support interval '{interval}' yet")

        end = datetime.now(timezone.utc)
        start = end - timedelta(days=lookback_days)

        # A bare crypto symbol ("BTC") resolves on Yahoo to the wrong
        # instrument (e.g. the Grayscale BTC Mini Trust ETF), so map it to
        # the proper "<TICKER>-USD" price before querying.
        ticker = resolve_symbol(symbol)

        try:
            df = yf.download(
                ticker,
                start=start,
                end=end,
                interval=interval,
                progress=False,
                auto_adjust=True,
            )
        except Exception as exc:  # yfinance can raise a variety of things
            raise ProviderError(f"yfinance request failed for '{symbol}': {exc}") from exc

        if df is None or df.empty:
            # An empty result here is ambiguous — it can mean a genuinely
            # unknown ticker, but just as easily a network/rate-limit issue.
            # Treat it as a retryable ProviderError so the router still
            # tries the secondary provider, rather than failing fast.
            raise ProviderError(f"No data returned by yfinance for symbol '{ticker}'")

        # yfinance can return MultiIndex columns for some calls — flatten if so.
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        candles = [
            Candle(
                timestamp=idx.to_pydatetime(),
                open=float(row["Open"]),
                high=float(row["High"]),
                low=float(row["Low"]),
                close=float(row["Close"]),
                volume=int(row["Volume"]),
            )
            for idx, row in df.iterrows()
        ]

        return OHLCVSeries(symbol=symbol, interval=interval, candles=candles, source=self.name)
