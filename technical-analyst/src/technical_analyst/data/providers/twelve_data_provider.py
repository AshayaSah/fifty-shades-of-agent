import httpx

from technical_analyst.config import settings
from technical_analyst.data.models import Candle, OHLCVSeries
from technical_analyst.data.providers.base import (
    DataProvider,
    ProviderError,
    SymbolNotFoundError,
)
from technical_analyst.utils.logging import get_logger

logger = get_logger(__name__)

_BASE_URL = "https://api.twelvedata.com/time_series"

# Twelve Data interval strings we support for now.
_INTERVAL_MAP = {"1d": "1day"}


class TwelveDataProvider(DataProvider):
    name = "twelve_data"

    def fetch(self, symbol: str, interval: str = "1d", lookback_days: int = 90) -> OHLCVSeries:
        if not settings.twelve_data_api_key:
            raise ProviderError("TWELVE_DATA_API_KEY is not configured")

        td_interval = _INTERVAL_MAP.get(interval)
        if td_interval is None:
            raise ProviderError(f"Twelve Data provider does not support interval '{interval}' yet")

        # Twelve Data's time_series endpoint takes an output size (bars),
        # not a date range — approximate trading days from calendar days.
        output_size = max(int(lookback_days * 5 / 7) + 5, 30)

        params = {
            "symbol": symbol,
            "interval": td_interval,
            "outputsize": output_size,
            "apikey": settings.twelve_data_api_key,
        }

        try:
            resp = httpx.get(_BASE_URL, params=params, timeout=10.0)
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPError as exc:
            raise ProviderError(f"Twelve Data request failed for '{symbol}': {exc}") from exc

        if data.get("status") == "error":
            message = data.get("message", "unknown error")
            if "not found" in message.lower() or "symbol" in message.lower():
                raise SymbolNotFoundError(f"Twelve Data: symbol '{symbol}' not found — {message}")
            raise ProviderError(f"Twelve Data error for '{symbol}': {message}")

        values = data.get("values")
        if not values:
            raise SymbolNotFoundError(f"No data returned by Twelve Data for symbol '{symbol}'")

        candles = [
            Candle(
                timestamp=row["datetime"],
                open=float(row["open"]),
                high=float(row["high"]),
                low=float(row["low"]),
                close=float(row["close"]),
                volume=int(float(row.get("volume", 0) or 0)),
            )
            for row in reversed(values)  # Twelve Data returns newest-first
        ]

        return OHLCVSeries(symbol=symbol, interval=interval, candles=candles, source=self.name)
