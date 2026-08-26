from dataclasses import dataclass, field

import pandas as pd


@dataclass
class Signal:
    verdict: str  # "bullish" | "bearish" | "neutral"
    confidence: float  # 0-1
    reasons: list[str] = field(default_factory=list)


def generate_signal(latest_row) -> Signal:
    """Rules-based v1 signal. Deliberately simple and transparent (each
    reason maps directly to one indicator) so the output is easy to
    justify to a human approving a trade downstream."""
    reasons: list[str] = []
    score = 0

    sma_50 = latest_row.get("sma_50")
    close = latest_row.get("close")
    if sma_50 is not None and close is not None and pd.notna(sma_50):
        if close > sma_50:
            score += 1
            reasons.append("Price above 50-period SMA (uptrend)")
        else:
            score -= 1
            reasons.append("Price below 50-period SMA (downtrend)")

    rsi = latest_row.get("rsi_14")
    if rsi is not None and pd.notna(rsi):
        if rsi < 30:
            score += 1
            reasons.append(f"RSI {rsi:.1f} — oversold, potential bounce")
        elif rsi > 70:
            score -= 1
            reasons.append(f"RSI {rsi:.1f} — overbought, potential pullback")
        else:
            reasons.append(f"RSI {rsi:.1f} — neutral range")

    macd_hist = latest_row.get("MACDh_12_26_9")
    if macd_hist is not None and pd.notna(macd_hist):
        if macd_hist > 0:
            score += 1
            reasons.append("MACD histogram positive (bullish momentum)")
        else:
            score -= 1
            reasons.append("MACD histogram negative (bearish momentum)")

    if score >= 2:
        verdict = "bullish"
    elif score <= -2:
        verdict = "bearish"
    else:
        verdict = "neutral"

    confidence = round(min(abs(score) / 3, 1.0), 2)
    return Signal(verdict=verdict, confidence=confidence, reasons=reasons)
