from abc import ABC, abstractmethod

from technical_analyst.data.models import OHLCVSeries


class ProviderError(Exception):
    """Raised when a provider fails to return usable data."""


class SymbolNotFoundError(ProviderError):
    """Raised when the symbol doesn't exist / has no data on this provider."""


class DataProvider(ABC):
    name: str

    @abstractmethod
    def fetch(self, symbol: str, interval: str, lookback_days: int) -> OHLCVSeries:
        """Fetch OHLCV data. Must raise ProviderError (or a subclass) on
        failure — never let a provider-specific exception leak out."""
        raise NotImplementedError
