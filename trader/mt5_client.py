import MetaTrader5 as mt5
from dotenv import load_dotenv
import os


class MT5ConnectionError(Exception):
    """Raised when MT5 terminal fails to initialize or is not running."""


load_dotenv()

_initialized = False


def connect() -> None:
    global _initialized
    if _initialized:
        return

    login = os.getenv("EXNESS_LOGIN")
    password = os.getenv("EXNESS_PASSWORD")
    server = os.getenv("EXNESS_SERVER")

    missing = [
        name
        for name, val in [
            ("EXNESS_LOGIN", login),
            ("EXNESS_PASSWORD", password),
            ("EXNESS_SERVER", server),
        ]
        if not val
    ]
    if missing:
        raise MT5ConnectionError(
            f"Missing environment variables: {', '.join(missing)}. "
            "Set them in .env or your environment."
        )

    if not mt5.initialize(login=int(login), password=password, server=server):
        code, comment = mt5.last_error()
        raise MT5ConnectionError(
            f"MT5 initialize failed: {comment} (code {code}). "
            "Make sure MetaTrader 5 terminal is running and logged in."
        )

    _initialized = True


def disconnect() -> None:
    global _initialized
    if _initialized:
        mt5.shutdown()
        _initialized = False


def get_account_info() -> dict:
    connect()
    info = mt5.account_info()
    if info is None:
        code, comment = mt5.last_error()
        raise MT5ConnectionError(
            f"Failed to get account info: {comment} (code {code})"
        )
    return {
        "balance": info.balance,
        "equity": info.equity,
        "margin": info.margin,
        "margin_free": info.margin_free,
        "leverage": info.leverage,
        "currency": info.currency,
    }


def get_positions() -> list[dict]:
    connect()
    positions = mt5.positions_get()
    if positions is None:
        return []
    return [
        {
            "ticket": p.ticket,
            "symbol": p.symbol,
            "volume": p.volume,
            "price_open": p.price_open,
            "price_current": p.price_current,
            "profit": p.profit,
            "type": "buy" if p.type == mt5.ORDER_TYPE_BUY else "sell",
        }
        for p in positions
    ]


ALIASES = {
    "apple": "AAPLm",
    "amazon": "AMZNm",
    "goog": "GOOGLm",
    "google": "GOOGLm",
    "meta": "META",
    "microsoft": "MSFTm",
    "tesla": "TSLAm",
    "nvidia": "NVDAm",
    "netflix": "NFLXm",
    "gold": "XAUUSDm",
    "silver": "XAGUSDm",
    "oil": "USOILm",
    "brent": "UKOILm",
    "natural gas": "XNGUSDm",
    "s&p 500": "US500m",
    "s&p500": "US500m",
    "sp500": "US500m",
    "nasdaq": "NAS100m",
    "dow": "US30m",
    "dow jones": "US30m",
    "ftse": "UK100m",
    "dax": "DE30m",
    "nikkei": "JP225m",
    "bitcoin": "BTCUSDm",
    "btc": "BTCUSDm",
    "ethereum": "ETHUSDm",
    "eth": "ETHUSDm",
    "solana": "SOLUSDm",
}


def _normalize(text: str) -> str:
    return text.strip().lower().replace("/", "").replace("#", "").replace(" ", "").replace("-", "")


def _symbol_path(symbol: str) -> str:
    return symbol


def _category_from_name(symbol: str) -> str:
    """Classify a symbol by its name when no path/MT5 info is available (pure/testable)."""
    base = symbol.upper().replace("#", "").rstrip("M")
    if not base:
        return "Unknown"

    # Metals
    if base in ("XAUUSD", "XAGUSD", "XPTUSD", "XPDUSD") or base.startswith(("XAU", "XAG", "XPT", "XPD")):
        return "Metals"
    # Energies
    if "OIL" in base or "XNG" in base or "GAS" in base or "WTI" in base or "BRENT" in base:
        return "Energies"
    # Crypto
    if base.startswith(("BTC", "ETH", "XRP", "LTC", "SOL", "ADA", "DOT", "BNB",
                        "LINK", "UNI", "BCH", "FIL", "AAVE", "DOGE", "XLM", "MATIC", "SHIB")):
        return "Crypto"
    # Indices: token prefix + trailing numeric family -> index
    index_tokens = ("US500", "US30", "NAS100", "AUS200", "DE30", "FR40", "UK100",
                    "JP225", "HK50", "IN50", "STOXX50", "SPX", "NDX")
    if any(base.startswith(t) for t in index_tokens):
        return "Indices"
    # Forex: a pair where the base/quote are currency codes
    currencies = {"USD", "EUR", "GBP", "JPY", "AUD", "NZD", "CAD", "CHF", "TRY",
                  "MXN", "ZAR", "HUF", "PLN", "SEK", "NOK", "DKK", "CZK", "SGD",
                  "CNH", "HKD", "ILS", "THB", "KRW", "BWP", "PKR", "RUB", "NZD"}
    if len(base) == 6 and base[:3] in currencies and base[3:] in currencies:
        return "Forex"
    # Stocks: fallback -> treat known-ticker-looking symbols as Stocks
    if base.isalpha() and len(base) <= 6:
        return "Stocks"
    return "Unknown"


def symbol_category(symbol: str) -> str:
    """Return a human-friendly category for a symbol.

    Uses the MT5 symbol path (e.g. 'Standard\\Stocks\\AAPLm') when available,
    falling back to name-pattern classification.
    """
    info = None
    try:
        connect()
        info = mt5.symbol_info(symbol)
    except Exception:
        info = None
    if info is not None and info.path and "\\" in info.path:
        parts = info.path.replace("/", "\\").split("\\")
        if len(parts) >= 2:
            return parts[-2]
    return _category_from_name(symbol)


def describe_symbol(symbol: str, category: str) -> str:
    return f"{symbol} ({category})"


def search_symbols(query: str, catalog: list[str] | None = None) -> list[dict]:
    """Search for matching MT5 symbols. Pure function (testable without MT5).

    catalog: optional list of symbol names to search. Defaults to the live MT5
    symbol list when running against a connected terminal.
    """
    if catalog is None:
        connect()
        catalog = [s.name for s in mt5.symbols_get()]
    if not catalog:
        return []

    nq = _normalize(query)
    if not nq:
        return []

    # 1. Exact match
    for s in catalog:
        if _normalize(s) == nq or _normalize(s).rstrip("m") == nq:
            return [_make_match(s)]

    # 2. Common-name alias
    if nq in ALIASES:
        target = ALIASES[nq]
        for s in catalog:
            if _normalize(s) == _normalize(target):
                return [_make_match(s)]

    # 3. Substring match on normalized symbol name
    matches = [
        _make_match(s)
        for s in catalog
        if nq in _normalize(s)
    ]
    if matches:
        return matches

    return []


def _make_match(symbol: str) -> dict:
    category = _category_from_name(symbol)
    return {
        "symbol": symbol,
        "category": category,
        "description": describe_symbol(symbol, category),
    }


def get_symbol_spec(symbol: str) -> dict:
    """Fetch pip value and point size for a symbol from MT5."""
    connect()
    info = mt5.symbol_info(symbol)
    if info is None:
        code, comment = mt5.last_error()
        raise MT5ConnectionError(
            f"Symbol '{symbol}' not found: {comment} (code {code})"
        )
    digits = info.digits
    if digits in (4, 5):
        pip_size = 10 * info.point
    else:
        pip_size = info.point
    pip_value = pip_size * info.trade_contract_size
    return {
        "symbol": symbol,
        "point": info.point,
        "digits": digits,
        "pip_size": pip_size,
        "pip_value": pip_value,
        "contract_size": info.trade_contract_size,
        "currency_base": info.currency_base,
        "currency_profit": info.currency_profit,
    }
