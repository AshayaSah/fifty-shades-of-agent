from technical_analyst.data.models import OHLCVSeries
from technical_analyst.data.providers.base import DataProvider, ProviderError, SymbolNotFoundError
from technical_analyst.data.providers.twelve_data_provider import TwelveDataProvider
from technical_analyst.data.providers.yfinance_provider import YFinanceProvider
from technical_analyst.utils.logging import get_logger

logger = get_logger(__name__)


class NoUsableDataError(Exception):
    """Raised when every configured provider failed for a symbol.
    There is currently no DB-based fallback for this — by design, if no
    provider has real data, the caller should surface 'no useful data'
    rather than silently serving something stale."""


class ProviderRouter:
    """Tries providers in order: yfinance (primary) -> Twelve Data (secondary).

    A SymbolNotFoundError from the primary is NOT retried on the secondary —
    if the symbol genuinely doesn't exist, trying another provider won't help,
    and it lets us fail fast with a clear message.
    """

    def __init__(self, providers: list[DataProvider] | None = None):
        self.providers = providers or [YFinanceProvider(), TwelveDataProvider()]

    def fetch(self, symbol: str, interval: str, lookback_days: int) -> OHLCVSeries:
        last_error: Exception | None = None

        for provider in self.providers:
            try:
                series = provider.fetch(symbol, interval, lookback_days)
                if series.candles:
                    return series
                last_error = ProviderError(f"{provider.name} returned an empty series")
            except SymbolNotFoundError as exc:
                logger.warning("%s: symbol not found for '%s'", provider.name, symbol)
                raise NoUsableDataError(str(exc)) from exc
            except ProviderError as exc:
                logger.warning("%s failed for '%s': %s", provider.name, symbol, exc)
                last_error = exc
                continue

        raise NoUsableDataError(
            f"No usable data for '{symbol}' — all providers failed. Last error: {last_error}"
        )
