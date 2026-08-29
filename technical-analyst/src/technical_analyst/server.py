from datetime import datetime, timezone

from fastmcp import FastMCP

from technical_analyst.analysis.indicators import MIN_CANDLES_REQUIRED, add_core_indicators
from technical_analyst.analysis.patterns import find_support_resistance
from technical_analyst.analysis.report import TechnicalAnalysisReport
from technical_analyst.analysis.signals import generate_signal
from technical_analyst.config import settings
from technical_analyst.data.cache import TTLCache
from technical_analyst.data.providers.router import NoUsableDataError, ProviderRouter
from technical_analyst.db import repository as repo
from technical_analyst.utils.logging import get_logger

logger = get_logger(__name__)

mcp = FastMCP("technical-analyst")
router = ProviderRouter()
cache = TTLCache(ttl_seconds=settings.cache_ttl_seconds)


@mcp.tool
def ping() -> str:
    """Sanity check tool — confirms the technical-analyst MCP is running."""
    return "technical-analyst MCP is alive"


@mcp.tool
def get_price_data(symbol: str, interval: str = "1d", lookback_days: int = 90) -> dict:
    """Fetch raw OHLCV price data for a stock symbol.

    Args:
        symbol: Ticker symbol, e.g. "AAPL".
        interval: Candle interval. Only "1d" is supported currently.
        lookback_days: How many calendar days of history to fetch.

    Returns:
        A dict with symbol, interval, source, and a list of candles
        (timestamp/open/high/low/close/volume). On failure, a dict with
        an "error" key instead.
    """
    try:
        series = _get_series(symbol, interval, lookback_days)
    except NoUsableDataError as exc:
        return {"error": str(exc)}
    return series.model_dump(mode="json")


@mcp.tool
def get_technical_analysis(symbol: str, interval: str = "1d", lookback_days: int = 90) -> dict:
    """Fetch price data and return a full technical analysis for a stock.

    Computes trend (SMA/EMA), momentum (RSI, MACD), volatility (Bollinger,
    ATR) and volume (OBV) indicators, basic support/resistance, and a
    combined bullish/bearish/neutral verdict with suggested stop-loss and
    take-profit levels (ATR-based). On success, the report is persisted
    to the technical-analyst Neon database (history + latest snapshot).

    Args:
        symbol: Ticker symbol, e.g. "AAPL".
        interval: Candle interval. Only "1d" is supported currently.
        lookback_days: How many calendar days of history to use.

    Returns:
        A dict matching TechnicalAnalysisReport, or {"error": ...} if no
        usable data was available from any provider, or not enough
        history was returned to compute indicators reliably.
    """
    try:
        series = _get_series(symbol, interval, lookback_days)
    except NoUsableDataError as exc:
        return {"error": str(exc)}

    df = series.to_dataframe()
    if len(df) < MIN_CANDLES_REQUIRED:
        return {
            "error": (
                f"Not enough price history for '{symbol}' to compute reliable "
                f"indicators ({len(df)} candles, need at least {MIN_CANDLES_REQUIRED}). "
                "Try a larger lookback_days."
            )
        }

    df = add_core_indicators(df)
    latest = df.iloc[-1]

    signal = generate_signal(latest)
    sr = find_support_resistance(df)

    atr = latest.get("atr_14")
    close = float(latest["close"])
    stop_loss = round(close - 1.5 * atr, 2) if atr and atr == atr else None  # atr==atr filters NaN
    take_profit = round(close + 3 * atr, 2) if atr and atr == atr else None

    report = TechnicalAnalysisReport(
        symbol=symbol,
        interval=interval,
        as_of=datetime.now(timezone.utc).isoformat(),
        source=series.source,
        verdict=signal.verdict,
        confidence=signal.confidence,
        reasons=signal.reasons,
        support=sr["support"],
        resistance=sr["resistance"],
        suggested_stop_loss=stop_loss,
        suggested_take_profit=take_profit,
        indicators={
            "close": round(close, 2),
            "sma_20": _safe_round(latest.get("sma_20")),
            "sma_50": _safe_round(latest.get("sma_50")),
            "ema_20": _safe_round(latest.get("ema_20")),
            "rsi_14": _safe_round(latest.get("rsi_14")),
            "atr_14": _safe_round(atr),
            "macd_hist": _safe_round(latest.get("MACDh_12_26_9")),
        },
    )

    try:
        repo.save_candles(series)
        repo.save_report(report)
    except Exception as exc:
        # DB write failure shouldn't block returning a valid analysis —
        # log it, but don't fail the tool call.
        logger.error("Failed to persist report for %s: %s", symbol, exc)

    return report.to_dict()


@mcp.tool
def get_analysis_history(symbol: str, limit: int = 10) -> dict:
    """Return past technical analysis reports for a symbol, most recent
    first. Useful as context — e.g. to see whether the verdict has been
    consistent or has recently flipped.

    Args:
        symbol: Ticker symbol, e.g. "AAPL".
        limit: Max number of past reports to return (default 10).
    """
    try:
        history = repo.get_report_history(symbol, limit=limit)
    except Exception as exc:
        return {"error": f"Could not read history for '{symbol}': {exc}"}
    return {"symbol": symbol, "count": len(history), "reports": history}


def _get_series(symbol: str, interval: str, lookback_days: int):
    key = f"{symbol}:{interval}:{lookback_days}"
    cached = cache.get(key)
    if cached is not None:
        return cached
    series = router.fetch(symbol, interval, lookback_days)
    cache.set(key, series)
    return series


def _safe_round(value, digits: int = 2):
    if value is None or value != value:  # NaN check without importing numpy/pandas here
        return None
    return round(float(value), digits)


def run():
    mcp.run()
