import os
import time

from dotenv import load_dotenv


class MT5ConnectionError(Exception):
    """Raised when the MT5 backend fails to initialize or is unreachable."""


def _is_linux() -> bool:
    return os.name == "posix"


# ---------------------------------------------------------------------------
# Linux backend: mt5linux bridge -> separate Wine + MetaTrader 5 sidecar.
# ---------------------------------------------------------------------------
def _linux_backend():
    import rpyc

    class _ExternalSidecarContainer:
        """Minimal RPyC shim that talks to an already-running mt5 sidecar.

        mt5linux's release tries to spawn its own Docker container on init. In
        our deployment the Wine + MT5 sidecar is a separate compose service, so
        we connect straight to its RPyC server using the same protocol
        (rpyc.classic) the library uses internally.
        """

        def __init__(self, host: str, port: int = 18812, timeout: int = 300):
            self.host = host
            self.port = port
            self._conn = None

            start = time.time()
            last_error = None
            while time.time() - start < timeout:
                try:
                    self._conn = rpyc.classic.connect(host, port)
                    self._conn._config["sync_request_timeout"] = timeout
                    break
                except Exception as exc:  # noqa: BLE001 - retry loop
                    last_error = exc
                    time.sleep(2)

            if self._conn is None:
                raise MT5ConnectionError(
                    f"Could not reach MT5 sidecar at {host}:{port} within "
                    f"{timeout}s. Last error: {last_error}. "
                    "Is the mt5-sidecar service running?"
                )

            # Match mt5linux's bootstrap so the standard proxy methods work.
            self.execute("import sys; sys.path.append('C:\\\\mt5libs')")
            self.execute("import MetaTrader5 as mt5")
            self.execute("import datetime")

        def eval(self, code: str):
            return rpyc.classic.obtain(self._conn.eval(code))

        def execute(self, code: str):
            self._conn.execute(code)

    def _make_bridge(host: str, port: int = 18812, timeout: int = 300):
        import mt5linux

        mt5 = object.__new__(mt5linux.MetaTrader5)
        # Skip the library's __init__ (which spawns a container) and wire our
        # own shim; every inherited proxy method reads self._container.eval.
        mt5._container = _ExternalSidecarContainer(host, port, timeout)
        return mt5

    return _make_bridge


# ---------------------------------------------------------------------------
# Windows backend: official native MetaTrader5 package + local MT5 terminal.
# ---------------------------------------------------------------------------
def _windows_backend():
    import MetaTrader5 as _mt5

    class _NativeMT5:
        """Thin facade over the native MetaTrader5 module so callers get a
        uniform instance-like API across Linux (bridge) and Windows (native)."""

        def initialize(self, *args, **kwargs):
            return _mt5.initialize(*args, **kwargs)

        def shutdown(self, *args, **kwargs):
            return _mt5.shutdown(*args, **kwargs)

        def last_error(self):
            return _mt5.last_error()

        def account_info(self, *args, **kwargs):
            return _mt5.account_info(*args, **kwargs)

        def positions_get(self, *args, **kwargs):
            return _mt5.positions_get(*args, **kwargs)

        def symbols_get(self, *args, **kwargs):
            return _mt5.symbols_get(*args, **kwargs)

        def symbol_info(self, *args, **kwargs):
            return _mt5.symbol_info(*args, **kwargs)

        def symbol_info_tick(self, *args, **kwargs):
            return _mt5.symbol_info_tick(*args, **kwargs)

        def order_send(self, *args, **kwargs):
            return _mt5.order_send(*args, **kwargs)

        def __getattr__(self, name):
            # Constants (ORDER_TYPE_BUY, TRADE_ACTION_DEAL, ...) come from the
            # module namespace on Windows.
            return getattr(_mt5, name)

    return _NativeMT5()


load_dotenv()

_bridge = None
_bridge_params: dict | None = None


def bridge():
    """Return the shared MT5 facade for the current platform.

    - Linux  : mt5linux proxy bound to the Wine/MT5 sidecar.
    - Windows: native MetaTrader5 wrapper against the local MT5 terminal.
    Raises ImportError if the backend dependency is missing on this platform.
    """
    global _bridge, _bridge_params

    if _is_linux():
        host = os.getenv("MT5_HOST", "mt5-sidecar")
        port = int(os.getenv("MT5_PORT", "18812"))
        timeout = int(os.getenv("MT5_CONNECT_TIMEOUT", "300"))
        params = ("linux", host, port, timeout)

        if _bridge is None or _bridge_params != params:
            _bridge = _linux_backend()(host, port, timeout)
            _bridge_params = params
        return _bridge

    if _bridge is None or _bridge_params != ("windows",):
        _bridge = _windows_backend()
        _bridge_params = ("windows",)
    return _bridge


def connect() -> None:
    """Ensure the MT5 backend is initialized and the terminal reachable."""
    mt5 = bridge()

    login = os.getenv("EXNESS_LOGIN")
    password = os.getenv("EXNESS_PASSWORD")
    server = os.getenv("EXNESS_SERVER")

    if _is_linux():
        # The Wine/MT5 sidecar may already be auto-logged-in via its own env
        # vars; a no-arg initialize() is enough when that's the case.
        ok = mt5.initialize() if not (login and server) else mt5.initialize(
            login=int(login), password=password, server=server
        )
    else:
        # Native Windows: initialize against the local MT5 terminal.
        ok = mt5.initialize()
        if ok and login and server:
            authorized = mt5.initialize(
                login=int(login), password=password, server=server
            )
            ok = authorized

    if not ok:
        code, comment = mt5.last_error()
        raise MT5ConnectionError(
            f"MT5 initialize failed: {comment} (code {code}). "
            "Ensure the MT5 terminal / sidecar is running and logged in."
        )


def disconnect() -> None:
    global _bridge, _bridge_params
    if _bridge is not None:
        try:
            _bridge.shutdown()
        except Exception:  # noqa: BLE001 - best effort on teardown
            pass
    _bridge = None
    _bridge_params = None


def get_account_info() -> dict:
    mt5 = bridge()
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
    mt5 = bridge()
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
        mt5 = bridge()
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
        mt5 = bridge()
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
    mt5 = bridge()
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
