from __future__ import annotations

import pandas as pd
import pytest

from app.models import DataResult, KissRegime, MarketIndexSnapshot, MarketSnapshot, RatesSnapshot, VamsSignal
from app.services import kiss_portfolio as kp
from app.services import kiss_regime as kr
from app.services import regime_history as rh
from app.services import signals as sig
from app.services import vams
from app.services import watchlist_snapshot as ws
from app.services.signals import compute_regime, summarize_alerts


class _Cfg:
    sleeves = {"equity": "SPY", "fixed_income": "AGG", "bitcoin": "BTC-USD", "cash": "USFR"}
    base_weights = {"equity": 0.6, "fixed_income": 0.3, "bitcoin": 0.1}
    regime_rules = {
        "goldilocks": {"equity": 0.6, "fixed_income": 0.3, "bitcoin": 0.1},
    }
    vams_multipliers = {"bullish": 1.0, "neutral": 0.5, "bearish": 0.0}
    alert_thresholds = {"large_move_1d": 0.03, "valuation_industry_gap": 0.2, "vams_bullish_threshold": 0.3, "vams_bearish_threshold": -0.3, "volatility_high_threshold": 0.35}
    market_watch_symbols = ["SPY"]
    regime_inputs = {
        "weak_score_threshold": 0.5,
        "growth": {
            "equity_trend_symbol": "SPY",
            "cyclical_symbol": "XLY",
            "defensive_symbol": "XLP",
            "copper_symbol": "CPER",
            "gold_symbol": "GLD",
        },
        "inflation": {"oil_symbol": "USO", "commodity_symbol": "DBC", "yield_symbol": "bc10_year"},
    }


def _prices(n=260):
    return pd.DataFrame({"report_date": pd.date_range("2024-01-01", periods=n, freq="B"), "close": range(n)})


class EdgeClient:
    def __init__(self, yields_empty=False, ratio_empty=False):
        self.yields_empty = yields_empty
        self.ratio_empty = ratio_empty

    def get_prices(self, symbol, force_refresh=False):
        if symbol == "EMPTY":
            return DataResult(pd.DataFrame())
        return DataResult(_prices())

    def get_price_ratio_history(self, a, b, force_refresh=False):
        if self.ratio_empty:
            return DataResult(pd.DataFrame())
        left = _prices()[["report_date", "close"]].rename(columns={"close": "left"})
        right = _prices()[["report_date", "close"]].rename(columns={"close": "right"})
        merged = left.merge(right, on="report_date")
        merged["ratio"] = merged["left"] / merged["right"]
        return DataResult(merged[["report_date", "ratio"]])

    def get_yield_series(self, force_refresh=False):
        if self.yields_empty:
            return DataResult(pd.DataFrame())
        return DataResult(
            pd.DataFrame(
                {
                    "report_date": pd.date_range("2024-01-01", periods=30, freq="B"),
                    "bc10_year": [0.05] * 30,
                }
            )
        )

    def latest_timestamp(self, frames):
        return None


def test_kiss_regime_empty_series():
    c = EdgeClient()
    r = kr.get_kiss_regime(c, _Cfg())
    assert r.regime in {"goldilocks", "reflation", "inflation", "deflation"}


def test_kiss_regime_yield_short_series():
    c = EdgeClient(yields_empty=False)

    class ShortY(EdgeClient):
        def get_yield_series(self, force_refresh=False):
            return DataResult(pd.DataFrame({"report_date": [pd.Timestamp("2024-01-01")], "bc10_year": [0.05]}))

    r = kr.get_kiss_regime(ShortY(), _Cfg())
    assert r.growth_direction in {"up", "down"}


def test_regime_history_helpers_empty():
    assert rh._close_series(pd.DataFrame()).empty
    assert rh._trend_series(pd.DataFrame(), 5).empty
    assert rh._ratio_trend_series(EdgeClient(ratio_empty=True), "SPY", "AGG").empty
    assert rh._yield_trend_series(EdgeClient(yields_empty=True), "bc10_year").empty


def test_classify_regime_corners():
    assert rh._classify_regime(0.1, -0.1) == "goldilocks"
    assert rh._classify_regime(0.1, 0.1) == "reflation"
    assert rh._classify_regime(-0.1, 0.1) == "inflation"
    assert rh._classify_regime(-0.1, -0.1) == "deflation"


def test_vams_helpers():
    assert vams._safe_return(pd.Series([1, 2, 3]), 5) == 0.0
    close, ts = vams._latest_close(pd.DataFrame())
    assert close.empty


def test_compute_regime_branches():
    mk = lambda **kw: MarketIndexSnapshot("SPY", 1.0, 0, 0, 0, 0, kw.get("m50", "above"), kw.get("m200", "above"), kw.get("m200b", "above"), None)
    m = MarketSnapshot(
        indices=[
            mk(m50="above", m200="above"),
            mk(m50="above", m200="above"),
            mk(m50="below", m200="below"),
            mk(m50="below", m200="below"),
        ],
        positive_participation_ratio=0.8,
        as_of=None,
    )
    r = RatesSnapshot(None, None, None, None, -0.01, -0.003, 0.004)
    wl = pd.DataFrame({"return_1m": [0.1, 0.1, 0.1]})
    out = compute_regime(m, r, wl)
    assert out.regime in {"Risk-On", "Risk-Off", "Neutral"}

    m2 = MarketSnapshot(indices=[mk(m50="above", m200="above")], positive_participation_ratio=0.1, as_of=None)
    r2 = RatesSnapshot(None, None, None, None, 0.01, 0.01, -0.01)
    wl2 = pd.DataFrame({"return_1m": [-0.1, -0.1, -0.1]})
    compute_regime(m2, r2, wl2)


def test_get_alert_flags_and_summarize():
    row = pd.Series(
        {
            "days_to_earnings": 5.0,
            "return_1d": 0.05,
            "ma50_state": "below",
            "ma200_state": "below",
            "ttm_pe_vs_industry": 0.25,
            "net_margin": -0.1,
            "revenue_yoy_growth": -0.05,
        }
    )
    rates = RatesSnapshot(pd.Timestamp("2024-01-01"), 0.04, 0.05, 0.05, -0.01, 0.0, 0.0)
    flags = sig.get_alert_flags("SPY", row, rates, {"large_move_1d": 0.03, "valuation_industry_gap": 0.2})
    assert flags
    assert summarize_alerts(pd.DataFrame()) == {"high_alerts": 0, "medium_alerts": 0, "total_alerts": 0}
    df = pd.DataFrame({"alert_count": [2], "high_alert_count": [1], "medium_alert_count": [1]})
    assert summarize_alerts(df)["total_alerts"] == 2


def test_watchlist_helpers_and_empty_paths():
    assert ws._latest_close_and_trend(pd.DataFrame()).get("close") is None
    assert ws._latest_value(pd.DataFrame(), "x") is None
    assert ws._latest_value(pd.DataFrame({"x": [float("nan")]}), "x") is None
    assert ws._next_earnings_days(pd.DataFrame()) is None


def test_kiss_portfolio_resets_and_second_snapshot(monkeypatch):
    monkeypatch.setattr(kp, "_PRIOR_SNAPSHOT", None)

    regime = KissRegime("goldilocks", 0.5, None, "up", "down", {}, None, [])
    vm = {
        "SPY": VamsSignal("SPY", "bullish", 0.5, 0.1, 0.1, 0.1, None, []),
        "AGG": VamsSignal("AGG", "neutral", 0.0, 0.1, 0.1, 0.1, None, []),
        "BTC-USD": VamsSignal("BTC-USD", "bearish", -0.5, 0.1, 0.1, 0.1, None, []),
    }
    kp.build_kiss_portfolio_snapshot(regime, vm, _Cfg())
    regime2 = KissRegime("inflation", 0.5, None, "down", "up", {}, None, [])
    kp.build_kiss_portfolio_snapshot(regime2, vm, _Cfg())
    monkeypatch.setattr(kp, "_PRIOR_SNAPSHOT", None)


def test_latest_transition_branches():
    assert rh._latest_transition("L", ["a"], [pd.Timestamp("2024-01-01")]) is not None
    tr = rh._latest_transition("L", ["a", "b"], [pd.Timestamp("2024-01-01"), pd.Timestamp("2024-01-02")])
    assert tr is not None


def test_indicator_from_price_empty_columns():
    ind = rh._indicator_from_price("SPY", pd.DataFrame({"report_date": [pd.Timestamp("2024-01-01")]}))
    assert ind.latest_value is None

