# Symbols that need normalizing before querying external price providers.
#
# Yahoo Finance (and Twelve Data) resolve a bare crypto symbol like "BTC"
# to a *different* instrument — e.g. "BTC" is Yahoo's "Grayscale Bitcoin
# Mini Trust ETF" (~$35), not Bitcoin the cryptocurrency. Real crypto prices
# live under the "<TICKER>-USD" convention. This map translates the common
# user-facing crypto names to the provider tickers so we don't silently
# analyze the wrong instrument.
CRYPTO_SYMBOL_MAP = {
    "BTC": "BTC-USD",
    "ETH": "ETH-USD",
    "SOL": "SOL-USD",
    "XRP": "XRP-USD",
    "ADA": "ADA-USD",
    "DOGE": "DOGE-USD",
    "DOT": "DOT-USD",
    "LTC": "LTC-USD",
    "LINK": "LINK-USD",
    "AVAX": "AVAX-USD",
    "MATIC": "MATIC-USD",
    "UNI": "UNI-USD",
    "BNB": "BNB-USD",
    "SHIB": "SHIB-USD",
    "ETC": "ETC-USD",
    "BCH": "BCH-USD",
}


def resolve_symbol(symbol: str) -> str:
    """Return the provider ticker for a user-facing symbol.

    Unknown symbols (stocks, ETFs, already-suffixed tickers) pass through
    unchanged. The comparison is case-insensitive but the canonical ticker
    is returned uppercased.
    """
    return CRYPTO_SYMBOL_MAP.get(symbol.upper(), symbol)
