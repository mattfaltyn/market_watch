import pandas as pd

from app.models import DataResult
from app.services.regime_history import build_regime_history, build_regime_overview_snapshot


class FakeConfig:
    sleeves = {"equity": "SPY", "fixed_income": "AGG", "bitcoin": "BTC-USD", "cash": "USFR"}
    alert_thresholds = {"vams_bullish_threshold": 0.1, "vams_bearish_threshold": -0.1, "volatility_high_threshold": 1.0}
    market_watch_symbols = ["SPY", "QQQ", "IWM", "BTC-USD", "GLD", "USO", "DBC"]
    regime_inputs = {
        "weak_score_threshold": 0.05,
        "growth": {
            "equity_trend_symbol": "SPY",
            "cyclical_symbol": "XLY",
            "defensive_symbol": "XLP",
            "copper_symbol": "CPER",
            "gold_symbol": "GLD",
        },
        "inflation": {
            "oil_symbol": "USO",
            "commodity_symbol": "DBC",
            "yield_symbol": "bc10_year",
        },
    }


class FakeClient:
    def __init__(self, mapping, yields):
        self.mapping = mapping
        self.yields = yields

    def get_prices(self, symbol, force_refresh=False):
        return DataResult(self.mapping[symbol])

    def get_price_ratio_history(self, symbol_a, symbol_b, force_refresh=False):
        left = self.mapping[symbol_a][["report_date", "close"]].rename(columns={"close": "left"})
        right = self.mapping[symbol_b][["report_date", "close"]].rename(columns={"close": "right"})
        merged = left.merge(right, on="report_date")
        merged["ratio"] = merged["left"] / merged["right"]
        return DataResult(merged[["report_date", "ratio"]])

    def get_yield_series(self, force_refresh=False):
        return DataResult(self.yields)

    def get_treasury_yields(self, force_refresh=False):
        return DataResult(self.yields)

    def latest_timestamp(self, frames):
        valid = [frame["report_date"].max() for frame in frames if not frame.empty]
        return max(valid).to_pydatetime() if valid else None


def _price_frame(start=100.0, step=1.0, periods=260):
    closes = [start + step * i for i in range(periods)]
    return pd.DataFrame({"report_date": pd.date_range("2024-01-01", periods=periods, freq="B"), "close": closes})


def test_build_regime_history_replays_labels():
    client = FakeClient(
        {
            "SPY": _price_frame(100, 1.0),
            "XLY": _price_frame(100, 0.8),
            "XLP": _price_frame(100, 0.2),
            "CPER": _price_frame(50, 0.5),
            "GLD": _price_frame(100, -0.1),
            "USO": _price_frame(100, -0.2),
            "DBC": _price_frame(100, -0.1),
            "QQQ": _price_frame(100, 0.7),
            "IWM": _price_frame(100, 0.6),
            "BTC-USD": _price_frame(1000, 5.0),
            "AGG": _price_frame(100, 0.2),
        },
        pd.DataFrame({"report_date": pd.date_range("2024-01-01", periods=260, freq="B"), "bc10_year": [0.05 - i * 0.0001 for i in range(260)], "bc2_year": [0.045 - i * 0.00005 for i in range(260)]}),
    )
    history = build_regime_history(client, FakeConfig())
    assert history
    assert history[-1].regime == "goldilocks"


def test_build_regime_overview_snapshot_is_history_backed():
    client = FakeClient(
        {
            "SPY": _price_frame(100, 1.0),
            "XLY": _price_frame(100, 0.8),
            "XLP": _price_frame(100, 0.2),
            "CPER": _price_frame(50, 0.5),
            "GLD": _price_frame(100, -0.1),
            "USO": _price_frame(100, -0.2),
            "DBC": _price_frame(100, -0.1),
            "QQQ": _price_frame(100, 0.7),
            "IWM": _price_frame(100, 0.6),
            "BTC-USD": _price_frame(1000, 5.0),
            "AGG": _price_frame(100, 0.2),
        },
        pd.DataFrame({"report_date": pd.date_range("2024-01-01", periods=260, freq="B"), "bc10_year": [0.05 - i * 0.0001 for i in range(260)], "bc2_year": [0.045 - i * 0.00005 for i in range(260)]}),
    )
    snapshot = build_regime_overview_snapshot(client, FakeConfig())
    assert snapshot.transitions
    assert snapshot.confirmations
