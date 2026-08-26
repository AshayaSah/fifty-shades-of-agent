import json
from pathlib import Path

import pandas as pd
import pytest

from technical_analyst.analysis.indicators import add_core_indicators
from technical_analyst.analysis.patterns import find_support_resistance
from technical_analyst.analysis.signals import generate_signal

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "sample_ohlcv.json"


def load_fixture_df() -> pd.DataFrame:
    data = json.loads(FIXTURE_PATH.read_text())
    df = pd.DataFrame(data["candles"])
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df.set_index("timestamp", inplace=True)
    df.sort_index(inplace=True)
    return df


@pytest.mark.skipif(not FIXTURE_PATH.exists(), reason="fixture not generated yet")
def test_indicators_present():
    df = add_core_indicators(load_fixture_df())
    for col in ["sma_20", "sma_50", "rsi_14", "atr_14"]:
        assert col in df.columns


@pytest.mark.skipif(not FIXTURE_PATH.exists(), reason="fixture not generated yet")
def test_rsi_bounds():
    df = add_core_indicators(load_fixture_df())
    rsi = df["rsi_14"].dropna()
    assert (rsi >= 0).all() and (rsi <= 100).all()


@pytest.mark.skipif(not FIXTURE_PATH.exists(), reason="fixture not generated yet")
def test_signal_has_verdict_and_reasons():
    df = add_core_indicators(load_fixture_df())
    signal = generate_signal(df.iloc[-1])
    assert signal.verdict in {"bullish", "bearish", "neutral"}
    assert len(signal.reasons) > 0


@pytest.mark.skipif(not FIXTURE_PATH.exists(), reason="fixture not generated yet")
def test_support_resistance_sane():
    df = add_core_indicators(load_fixture_df())
    sr = find_support_resistance(df)
    assert sr["support"] <= sr["resistance"]
