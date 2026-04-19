import pandas as pd

from app.models import DataResult
from app.services.vams import get_vams_signal, get_vams_signal_history


class FakeClient:
    def __init__(self, frame):
        self.frame = frame

    def get_prices(self, symbol, force_refresh=False):
        return DataResult(self.frame)


def _frame(start=100.0, step=1.0):
    closes = [start + step * i for i in range(260)]
    return pd.DataFrame({"report_date": pd.date_range("2024-01-01", periods=260, freq="B"), "close": closes})


def _short_frame(start=100.0, step=1.0):
    closes = [start + step * i for i in range(30)]
    return pd.DataFrame({"report_date": pd.date_range("2024-01-01", periods=30, freq="B"), "close": closes})


def test_vams_bullish():
    signal = get_vams_signal(FakeClient(_frame(100, 1.0)), "SPY", {"vams_bullish_threshold": 0.1, "vams_bearish_threshold": -0.1, "volatility_high_threshold": 1.0})
    assert signal.state == "bullish"


def test_vams_bearish():
    signal = get_vams_signal(FakeClient(_frame(300, -1.0)), "SPY", {"vams_bullish_threshold": 0.1, "vams_bearish_threshold": -0.1, "volatility_high_threshold": 1.0})
    assert signal.state == "bearish"


def test_vams_history_tracks_state_series():
    history = get_vams_signal_history(
        FakeClient(_frame(100, 1.0)),
        ["SPY"],
        {"vams_bullish_threshold": 0.1, "vams_bearish_threshold": -0.1, "volatility_high_threshold": 1.0},
    )
    assert history["SPY"]
    assert history["SPY"][-1].state == "bullish"


def test_vams_sparse_history_uses_distinct_trend_and_momentum_fallbacks():
    signal = get_vams_signal(
        FakeClient(_short_frame(100, 1.0)),
        "SPY",
        {"vams_bullish_threshold": 0.1, "vams_bearish_threshold": -0.1, "volatility_high_threshold": 1.0},
    )
    assert signal.trend == 0.0
    assert signal.momentum > 0.0
