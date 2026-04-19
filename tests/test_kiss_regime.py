import pandas as pd

from app.models import DataResult
from app.services.kiss_regime import get_kiss_regime


class FakeConfig:
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

    def last_price_source(self, symbol):
        return None

    def get_yield_series(self, force_refresh=False):
        return DataResult(self.yields)

    def latest_timestamp(self, frames):
        valid = [frame["report_date"].max() for frame in frames if not frame.empty]
        return max(valid).to_pydatetime() if valid else None


def _price_frame(start=100.0, step=1.0):
    closes = [start + step * i for i in range(80)]
    return pd.DataFrame({"report_date": pd.date_range("2024-01-01", periods=80, freq="B"), "close": closes})


def test_get_kiss_regime_goldilocks():
    client = FakeClient(
        {
            "SPY": _price_frame(100, 1.0),
            "XLY": _price_frame(100, 0.8),
            "XLP": _price_frame(100, 0.2),
            "CPER": _price_frame(50, 0.5),
            "GLD": _price_frame(100, -0.1),
            "USO": _price_frame(100, -0.2),
            "DBC": _price_frame(100, -0.1),
        },
        pd.DataFrame({"report_date": pd.date_range("2024-01-01", periods=40, freq="B"), "bc10_year": [0.05 - i * 0.0002 for i in range(40)]}),
    )
    regime = get_kiss_regime(client, FakeConfig())
    assert regime.regime == "goldilocks"


def test_get_kiss_regime_inflation():
    client = FakeClient(
        {
            "SPY": _price_frame(100, -0.5),
            "XLY": _price_frame(100, -0.3),
            "XLP": _price_frame(100, 0.2),
            "CPER": _price_frame(50, -0.2),
            "GLD": _price_frame(100, 0.1),
            "USO": _price_frame(100, 0.8),
            "DBC": _price_frame(100, 0.5),
        },
        pd.DataFrame({"report_date": pd.date_range("2024-01-01", periods=40, freq="B"), "bc10_year": [0.03 + i * 0.0002 for i in range(40)]}),
    )
    regime = get_kiss_regime(client, FakeConfig())
    assert regime.regime == "inflation"


def test_get_kiss_regime_marks_unavailable_cyclical():
    empty = pd.DataFrame(columns=["report_date", "close"])
    client = FakeClient(
        {
            "SPY": _price_frame(100, 1.0),
            "XLY": empty,
            "XLP": _price_frame(100, 0.2),
            "CPER": _price_frame(50, 0.5),
            "GLD": _price_frame(100, -0.1),
            "USO": _price_frame(100, -0.2),
            "DBC": _price_frame(100, -0.1),
        },
        pd.DataFrame({"report_date": pd.date_range("2024-01-01", periods=40, freq="B"), "bc10_year": [0.05 - i * 0.0002 for i in range(40)]}),
    )
    regime = get_kiss_regime(client, FakeConfig())
    assert "cyclical_defensive_ratio" in regime.unavailable_components
    assert regime.component_scores["cyclical_defensive_ratio"] is None
