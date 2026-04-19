"""Targeted tests for remaining branch/line coverage gaps."""

from __future__ import annotations

from unittest import mock

import pandas as pd

from app.components import ui
from app.models import (
    ConfirmationSnapshot,
    DataResult,
    IndicatorSnapshot,
    KissRegime,
    MarketIndexSnapshot,
    MarketSnapshot,
    RatesSnapshot,
    RegimeOverviewSnapshot,
    TickerDetailBundle,
    VamsHistoryPoint,
    VamsSignal,
)
from app.pages.overview import render_regime_overview
from app.pages.ticker_detail import render_ticker_detail
from app.services import kiss_portfolio as kp
from app.services import kiss_regime as kr
from app.services import regime_history as rh
from app.services import vams
from app.services.signals import compute_regime
from app.services.watchlist_snapshot import build_watchlist_snapshot


def test_ui_make_line_skips_missing_y_column():
    df = pd.DataFrame({"report_date": [pd.Timestamp("2024-01-01")], "y": [1.0]})
    assert ui.make_line_chart(df, "report_date", ["y", "ghost"], "t") is not None


def test_ui_format_numeric_variants_in_table():
    df = pd.DataFrame(
        {
            "s": ["txt"],
            "big": [5000.0],
            "ret": [0.04],
            "days_to_x": [3.0],
            "plain_num": [1500.0],
            "obj_str": pd.Series(["strcell"], dtype=object),
            "ts": [pd.Timestamp("2024-03-01")],
            "none_cell": [None],
            "odd": [object()],
        }
    )
    assert ui.make_table(df) is not None


def test_ui_format_numeric_private():
    assert ui._format_numeric(None, "c") == "—"
    assert ui._format_numeric(float("nan"), "c") == "—"
    assert "2024" in str(ui._format_numeric(pd.Timestamp("2024-06-01"), "c"))
    assert ui._format_numeric(object(), "c") is not None


def test_overview_benchmark_price_branches():
    regime = KissRegime("goldilocks", 0.5, None, "up", "down", {}, None, [])
    inds = [
        IndicatorSnapshot("SPY", None, None, None, None, "x", None, None),
        IndicatorSnapshot("QQQ", 100.0, 0.01, 0.02, 0.03, "x", None, None),
        IndicatorSnapshot("IWM", 50.0, 0.01, None, None, "x", None, None),
        IndicatorSnapshot("XLF", 30.0, None, 0.02, None, "x", None, None),
    ]
    snap = RegimeOverviewSnapshot(
        regime=regime,
        regime_history=[],
        indicators=inds,
        confirmations=[
            ConfirmationSnapshot("SPY", "E", "bullish", 0.5, 0.1, 0.1, 0.1, None, None),
        ],
        transitions=[],
        as_of=None,
        summary_text="s",
    )
    assert render_regime_overview(snap, []) is not None


def test_ticker_detail_eps_format_branch():
    bundle = TickerDetailBundle(
        symbol="SPY",
        info=pd.DataFrame(),
        price=pd.DataFrame({"report_date": [pd.Timestamp("2024-01-01")], "close": [100.0]}),
        valuation={"ttm_pe": pd.DataFrame()},
        quality={"roe": pd.DataFrame({"report_date": [pd.Timestamp("2024-01-01")], "roe": [float("nan")]})},
        growth={"eps_yoy_growth": pd.DataFrame({"report_date": [pd.Timestamp("2024-01-01")], "eps_yoy_growth": [3.5]})},
        news=pd.DataFrame(),
        filings=pd.DataFrame(),
        calendar=pd.DataFrame(),
        revenue_breakdown={"segment": pd.DataFrame(), "geography": pd.DataFrame()},
        transcripts=pd.DataFrame(),
        alerts=[],
        errors=[],
        role_label=None,
    )
    assert render_ticker_detail(bundle) is not None


def test_latest_transition_no_paired_dates():
    assert rh._latest_transition("L", ["a"], [None]) is None


def test_indicator_from_price_all_nan_close():
    df = pd.DataFrame({"report_date": [pd.Timestamp("2024-01-01")], "close": [float("nan")]})
    ind = rh._indicator_from_price("SPY", df)
    assert ind.latest_value is None


def test_vams_score_frame_empty_after_dropna():
    df = pd.DataFrame({"report_date": [pd.Timestamp("2024-01-01")], "close": [float("nan")]})
    out = vams._score_frame(df, {"vams_bullish_threshold": 0.3, "vams_bearish_threshold": -0.3, "volatility_high_threshold": 0.35})
    assert out.empty


def test_vams_score_frame_missing_close_column():
    df = pd.DataFrame({"report_date": [pd.Timestamp("2024-01-01")], "open": [1.0]})
    assert vams._score_frame(df, {"vams_bullish_threshold": 0.3, "vams_bearish_threshold": -0.3, "volatility_high_threshold": 0.35}).empty


def test_kiss_portfolio_tracks_changes(monkeypatch):
    monkeypatch.setattr(kp, "_PRIOR_SNAPSHOT", None)
    from app.models import KissPortfolioSnapshot, SleeveAllocation, SignalChange

    regime = KissRegime("goldilocks", 0.5, None, "up", "down", {}, None, [])
    vm = {
        "SPY": VamsSignal("SPY", "bullish", 0.5, 0.1, 0.1, 0.1, None, []),
        "AGG": VamsSignal("AGG", "neutral", 0.0, 0.1, 0.1, 0.1, None, []),
        "BTC-USD": VamsSignal("BTC-USD", "neutral", 0.0, 0.1, 0.1, 0.1, None, []),
    }
    kp.build_kiss_portfolio_snapshot(regime, vm, _pcfg())
    vm2 = {
        "SPY": VamsSignal("SPY", "neutral", 0.0, 0.1, 0.1, 0.1, None, []),
        "AGG": VamsSignal("AGG", "bearish", -0.5, 0.1, 0.1, 0.1, None, []),
        "BTC-USD": VamsSignal("BTC-USD", "neutral", 0.0, 0.1, 0.1, 0.1, None, []),
    }
    kp.build_kiss_portfolio_snapshot(regime, vm2, _pcfg())
    regime3 = KissRegime("inflation", 0.5, None, "down", "up", {}, None, [])
    kp.build_kiss_portfolio_snapshot(regime3, vm2, _pcfg())
    monkeypatch.setattr(kp, "_PRIOR_SNAPSHOT", None)


def _pcfg():
    class C:
        sleeves = {"equity": "SPY", "fixed_income": "AGG", "bitcoin": "BTC-USD", "cash": "USFR"}
        base_weights = {"equity": 0.6, "fixed_income": 0.3, "bitcoin": 0.1}
        regime_rules = {
            "goldilocks": {"equity": 0.6, "fixed_income": 0.3, "bitcoin": 0.1},
            "inflation": {"equity": 0.3, "fixed_income": 0.15, "bitcoin": 0.05},
        }
        vams_multipliers = {"bullish": 1.0, "neutral": 0.5, "bearish": 0.0}

    return C()


class WLClient:
    def get_prices(self, symbol, force_refresh=False):
        return DataResult(pd.DataFrame({"report_date": [pd.Timestamp("2024-01-01")], "close": [1.0]}))

    def get_beta(self, symbol, benchmark, force_refresh=False):
        return DataResult(pd.DataFrame({"report_date": [pd.Timestamp("2024-01-01")], "beta": [1.0]}))

    def get_calendar(self, symbol, force_refresh=False):
        return DataResult(pd.DataFrame({"wrong_col": [1]}))

    def get_news(self, symbol, force_refresh=False):
        return DataResult(pd.DataFrame())

    def get_filings(self, symbol, force_refresh=False):
        return DataResult(pd.DataFrame())

    def get_metric_frame(self, symbol, method_name, ttl=None, force_refresh=False):
        return DataResult(pd.DataFrame())

    def get_treasury_yields(self, force_refresh=False):
        return DataResult(
            pd.DataFrame({"report_date": [pd.Timestamp("2024-01-01")], "bc2_year": [0.04], "bc10_year": [0.05]})
        )


def test_watchlist_calendar_and_filings_edges():
    class CalClient(WLClient):
        def get_calendar(self, symbol, force_refresh=False):
            return DataResult(pd.DataFrame({"earning_date": [pd.Timestamp("2000-01-01")]}))

    build_watchlist_snapshot(CalClient(), ["SPY"], "SPY", {"large_move_1d": 0.01, "valuation_industry_gap": 0.2})

    class FilingsClient(WLClient):
        def get_filings(self, symbol, force_refresh=False):
            return DataResult(pd.DataFrame({"filing_date": [pd.Timestamp("2000-01-01")], "form_type": ["8-K"]}))

    build_watchlist_snapshot(FilingsClient(), ["SPY"], "SPY", {"large_move_1d": 0.01, "valuation_industry_gap": 0.2})

    class NaNCalClient(WLClient):
        def get_calendar(self, symbol, force_refresh=False):
            return DataResult(pd.DataFrame({"earning_date": [float("nan")]}))

    build_watchlist_snapshot(NaNCalClient(), ["SPY"], "SPY", {"large_move_1d": 0.01, "valuation_industry_gap": 0.2})


def test_get_vams_signal_empty_prices():
    class NoPrice:
        def get_prices(self, *a, **k):
            return DataResult(pd.DataFrame())

    out = vams.get_vams_signal(
        NoPrice(),
        "SPY",
        {"vams_bullish_threshold": 0.3, "vams_bearish_threshold": -0.3, "volatility_high_threshold": 0.35},
    )
    assert out.state == "neutral"


def test_vams_fallback_all_zero_closes():
    z = pd.Series([0.0] * 60)
    vams._fallback_scores(z)


def test_kiss_regime_trend_zero_ma():
    close = pd.Series([0.0] * 60)
    assert kr._trend_score_optional(close, 50) is None


def test_kiss_regime_trend_short_series():
    assert kr._trend_score_optional(pd.Series([1.0] * 10), 50) is None


def test_kiss_regime_ratio_empty_paths():
    class Split:
        def get_prices(self, sym, **kwargs):
            if sym == "A":
                return DataResult(pd.DataFrame({"report_date": [pd.Timestamp("2024-01-01")], "close": [1.0]}))
            return DataResult(pd.DataFrame({"report_date": [pd.Timestamp("2025-01-01")], "close": [1.0]}))

    assert kr._ratio_trend(Split(), "A", "B") == (None, None)

    class LeftEmpty:
        def get_prices(self, sym, **kwargs):
            return DataResult(pd.DataFrame())

    assert kr._ratio_trend(LeftEmpty(), "A", "B") == (None, None)

    class ZeroRatio:
        def get_prices(self, sym, **kwargs):
            return DataResult(pd.DataFrame({"report_date": [pd.Timestamp("2024-01-01")], "close": [0.0]}))

    assert kr._ratio_trend(ZeroRatio(), "A", "B") == (None, None)


def test_kiss_regime_ratio_all_nan_ratio_values():
    class AllNanRatioDen:
        def get_prices(self, sym, **kwargs):
            if sym == "A":
                return DataResult(
                    pd.DataFrame({"report_date": [pd.Timestamp("2024-01-01")], "close": [float("nan")]})
                )
            return DataResult(pd.DataFrame({"report_date": [pd.Timestamp("2024-01-01")], "close": [1.0]}))

    assert kr._ratio_trend(AllNanRatioDen(), "A", "B") == (None, None)


def test_kiss_regime_latest_and_yield():
    assert kr._latest_close(pd.DataFrame({"x": [1]})).empty

    class EmptyYield:
        def get_yield_series(self, **kwargs):
            return DataResult(pd.DataFrame())

    assert kr._yield_trend(EmptyYield(), "bc10_year") == (None, None)

    class ShortYield:
        def get_yield_series(self, **kwargs):
            return DataResult(
                pd.DataFrame(
                    {
                        "report_date": pd.date_range("2024-01-01", periods=10, freq="B"),
                        "bc10_year": [0.05] * 10,
                    }
                )
            )

    yv, _ts = kr._yield_trend(ShortYield(), "bc10_year")
    assert yv is None


def test_compute_regime_skips_monthly_yield_when_none():
    m = MarketSnapshot(indices=[], positive_participation_ratio=0.5, as_of=None)
    r = RatesSnapshot(None, None, None, None, 0.02, 0.01, None)
    compute_regime(m, r, pd.DataFrame())


def test_compute_regime_middle_buckets_and_neutral_score():
    def mi(m50="above", m200="above"):
        return MarketIndexSnapshot("SPY", 1.0, 0.0, 0.0, 0.0, 0.0, "above", m50, m200, None)

    m = MarketSnapshot(indices=[mi(), mi()], positive_participation_ratio=0.5, as_of=None)
    r = RatesSnapshot(None, None, None, None, 0.02, 0.0, 0.001)
    wl = pd.DataFrame({"return_1m": [0.1] * 5 + [-0.1] * 5})
    out = compute_regime(m, r, wl)
    assert out.regime in {"Risk-On", "Risk-Off", "Neutral"}


def test_compute_regime_exhaustive_branches():
    def mi(m50="above", m200="above"):
        return MarketIndexSnapshot("SPY", 1.0, 0.0, 0.0, 0.0, 0.0, "above", m50, m200, None)

    m = MarketSnapshot(
        indices=[
            mi("above", "above"),
            mi("above", "above"),
            mi("below", "below"),
            mi("below", "below"),
        ],
        positive_participation_ratio=0.8,
        as_of=None,
    )
    r = RatesSnapshot(None, None, None, None, -0.01, -0.01, -0.01)
    wl = pd.DataFrame({"return_1m": [0.05, 0.05, 0.05, 0.05, 0.05, 0.05]})
    compute_regime(m, r, wl)

    r2 = RatesSnapshot(None, None, None, None, 0.02, 0.01, 0.01)
    compute_regime(m, r2, wl)

    m2 = MarketSnapshot(indices=[mi()], positive_participation_ratio=0.1, as_of=None)
    compute_regime(m2, r, pd.DataFrame())


def test_build_regime_overview_snapshot_none_transition_branch():
    from app.config import load_config
    from app.services import regime_history as rhmod
    from app.services.regime_history import build_regime_overview_snapshot
    from tests.routing_fake import RoutingFakeClient

    cfg = load_config()

    with mock.patch.object(rhmod, "get_vams_signal_history", return_value={"SPY": [], "AGG": [], "BTC-USD": []}):
        build_regime_overview_snapshot(RoutingFakeClient(), cfg, force_refresh=False)

    hp = VamsHistoryPoint(pd.Timestamp("2024-01-01"), "bullish", 0.1, 0.1, 0.1, 0.1)
    with mock.patch.object(
        rhmod,
        "get_vams_signal_history",
        return_value={"SPY": [hp], "AGG": [hp], "BTC-USD": [hp]},
    ):
        build_regime_overview_snapshot(RoutingFakeClient(), cfg, force_refresh=False)
