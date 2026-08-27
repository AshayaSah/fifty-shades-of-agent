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
