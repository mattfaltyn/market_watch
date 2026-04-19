from __future__ import annotations

import pandas as pd

from app.models import DataResult
from app.services.market_snapshot import BENCHMARKS, build_market_snapshot, build_rates_snapshot


class MiniClient:
    def __init__(self, prices, yields):
        self._prices = prices
        self._yields = yields

    def get_prices(self, symbol, force_refresh=False):
        return DataResult(self._prices.get(symbol, pd.DataFrame()))

    def get_treasury_yields(self, force_refresh=False):
        return DataResult(self._yields)


def _series(n=250):
    return pd.DataFrame(
        {"report_date": pd.date_range("2024-01-01", periods=n, freq="B"), "close": [100.0 + i * 0.1 for i in range(n)]}
    )


def test_latest_return_short_series():
    from app.services import market_snapshot as ms

    s = pd.Series([1.0, 2.0], dtype=float)
    assert ms._latest_return(s, 5) is None


def test_ma_state_short_series():
    from app.services import market_snapshot as ms

    s = pd.Series([1.0, 2.0], dtype=float)
    assert ms._ma_state(s, 50) == "unavailable"


def test_build_market_snapshot_empty_price_columns():
    c = MiniClient({"SPY": pd.DataFrame({"report_date": [], "close": []})}, _series(5))
    snap = build_market_snapshot(c, symbols=["SPY"])
    assert snap.indices[0].close is None


def test_build_market_snapshot_missing_close_column():
    c = MiniClient({"SPY": pd.DataFrame({"report_date": [pd.Timestamp("2024-01-01")], "open": [1.0]})}, _series(5))
    snap = build_market_snapshot(c, symbols=["SPY"])
    assert snap.indices[0].ma20_state == "unavailable"


def test_build_market_snapshot_full_path_and_default_symbols():
    full = _series(250)
    mapping = {sym: full for sym in BENCHMARKS}
    c = MiniClient(mapping, _series(5))
    snap = build_market_snapshot(c, symbols=None)
    assert len(snap.indices) == len(BENCHMARKS)
    assert snap.indices[0].close is not None
    assert snap.positive_participation_ratio >= 0.0


def test_build_market_snapshot_insufficient_for_vol():
    short = _series(15)
    c = MiniClient({"SPY": short}, _series(5))
    snap = build_market_snapshot(c, symbols=["SPY"])
    assert snap.indices[0].realized_vol_20d is None


def test_build_rates_snapshot_empty():
    c = MiniClient({}, pd.DataFrame())
    rates = build_rates_snapshot(c)
    assert rates.y10 is None


def test_build_rates_snapshot_full():
    y = pd.DataFrame(
        {
            "report_date": pd.date_range("2024-01-01", periods=30, freq="B"),
            "bc2_year": [0.04 + i * 1e-5 for i in range(30)],
            "bc10_year": [0.045 + i * 1e-5 for i in range(30)],
            "bc30_year": [0.048] * 30,
        }
    )
    c = MiniClient({}, y)
    rates = build_rates_snapshot(c)
    assert rates.y10 is not None
    assert rates.spread_10y_2y is not None
