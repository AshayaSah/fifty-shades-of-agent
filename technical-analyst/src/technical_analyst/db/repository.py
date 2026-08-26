import json

from technical_analyst.analysis.report import TechnicalAnalysisReport
from technical_analyst.data.models import OHLCVSeries
from technical_analyst.db.connection import get_connection
from technical_analyst.utils.logging import get_logger

logger = get_logger(__name__)


def save_candles(series: OHLCVSeries) -> None:
    """Upserts candles — safe to call with overlapping date ranges."""
    if not series.candles:
        return

    rows = [
        (
            series.symbol,
            series.interval,
            c.timestamp,
            c.open,
            c.high,
            c.low,
            c.close,
            c.volume,
            series.source,
        )
        for c in series.candles
    ]

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.executemany(
                """
                INSERT INTO price_candles
                    (symbol, interval, ts, open, high, low, close, volume, source)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (symbol, interval, ts) DO NOTHING
                """,
                rows,
            )
        conn.commit()
    logger.info("Saved %d candles for %s (%s)", len(rows), series.symbol, series.interval)


def save_report(report: TechnicalAnalysisReport) -> None:
    """Writes the report to history (append-only) and upserts the
    'latest' snapshot, in a single transaction."""
    reasons_json = json.dumps(report.reasons)
    indicators_json = json.dumps(report.indicators)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO technical_analysis_reports
                    (symbol, interval, as_of, source, verdict, confidence, reasons,
                     support, resistance, suggested_stop_loss, suggested_take_profit, indicators)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    report.symbol,
                    report.interval,
                    report.as_of,
                    report.source,
                    report.verdict,
                    report.confidence,
                    reasons_json,
                    report.support,
                    report.resistance,
                    report.suggested_stop_loss,
                    report.suggested_take_profit,
                    indicators_json,
                ),
            )
            cur.execute(
                """
                INSERT INTO latest_technical_analysis
                    (symbol, interval, as_of, source, verdict, confidence, reasons,
                     support, resistance, suggested_stop_loss, suggested_take_profit,
                     indicators, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, now())
                ON CONFLICT (symbol) DO UPDATE SET
                    interval = EXCLUDED.interval,
                    as_of = EXCLUDED.as_of,
                    source = EXCLUDED.source,
                    verdict = EXCLUDED.verdict,
                    confidence = EXCLUDED.confidence,
                    reasons = EXCLUDED.reasons,
                    support = EXCLUDED.support,
                    resistance = EXCLUDED.resistance,
                    suggested_stop_loss = EXCLUDED.suggested_stop_loss,
                    suggested_take_profit = EXCLUDED.suggested_take_profit,
                    indicators = EXCLUDED.indicators,
                    updated_at = now()
                """,
                (
                    report.symbol,
                    report.interval,
                    report.as_of,
                    report.source,
                    report.verdict,
                    report.confidence,
                    reasons_json,
                    report.support,
                    report.resistance,
                    report.suggested_stop_loss,
                    report.suggested_take_profit,
                    indicators_json,
                ),
            )
        conn.commit()
    logger.info("Saved technical analysis report for %s", report.symbol)


def get_latest_report(symbol: str) -> dict | None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT symbol, interval, as_of, source, verdict, confidence, reasons, "
                "support, resistance, suggested_stop_loss, suggested_take_profit, "
                "indicators, updated_at FROM latest_technical_analysis WHERE symbol = %s",
                (symbol,),
            )
            row = cur.fetchone()
            if row is None:
                return None
            columns = [desc[0] for desc in cur.description]
            return dict(zip(columns, row))


def get_report_history(symbol: str, limit: int = 10) -> list[dict]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT symbol, interval, as_of, source, verdict, confidence, reasons, "
                "support, resistance, suggested_stop_loss, suggested_take_profit, "
                "indicators, created_at FROM technical_analysis_reports "
                "WHERE symbol = %s ORDER BY as_of DESC LIMIT %s",
                (symbol, limit),
            )
            rows = cur.fetchall()
            columns = [desc[0] for desc in cur.description]
            return [dict(zip(columns, row)) for row in rows]
