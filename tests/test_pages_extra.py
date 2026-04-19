from __future__ import annotations

import pandas as pd

from app.models import (
    ConfirmationSnapshot,
    IndicatorSnapshot,
    KissRegime,
    RegimeOverviewSnapshot,
    SignalTransition,
)
from app.pages.implementation import render_implementation
from app.pages.overview import render_regime_overview
from app.pages.ticker_detail import render_ticker_detail
from app.pages.watchlist import render_watchlist
from app.models import KissPortfolioSnapshot, SleeveAllocation, TickerDetailBundle, VamsSignal


def test_render_watchlist_empty_and_nonempty():
    empty = render_watchlist(pd.DataFrame(), [])
    assert empty is not None
    df = pd.DataFrame(
        {
            "symbol": ["SPY"],
            "close": [100.0],
            "return_1d": [0.01],
            "return_5d": [0.02],
            "return_1m": [0.03],
            "beta_1y": [1.0],
            "days_to_earnings": [5.0],
            "ttm_pe": [20.0],
            "industry_ttm_pe": [18.0],
            "recent_news_7d": [2],
            "filing_count_30d": [1],
            "alert_count": [0],
            "alerts": [["a"]],
            "high_alert_count": [0],
        }
    )
    assert render_watchlist(df, ["warn"]) is not None


def test_ticker_detail_mini_stat_formats():
    bundle = TickerDetailBundle(
        symbol="SPY",
        info=pd.DataFrame(),
        price=pd.DataFrame({"report_date": [pd.Timestamp("2024-01-01")], "close": [100.0]}),
        valuation={"ttm_pe": pd.DataFrame()},
        quality={"roe": pd.DataFrame({"report_date": [pd.Timestamp("2024-01-01")], "roe": [2.5]})},
        growth={"revenue_yoy_growth": pd.DataFrame()},
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


def test_implementation_action_rows_branches():
    regime = KissRegime("goldilocks", 0.5, None, "up", "down", {}, None, [])
    snap = KissPortfolioSnapshot(
        regime=regime,
        sleeves=[
            SleeveAllocation("e", "SPY", 0.6, 0.5, 0.3, "bullish", 1.0, "G", 0.1),
            SleeveAllocation("f", "AGG", 0.3, 0.2, 0.35, "neutral", 0.5, "G", -0.05),
            SleeveAllocation("b", "BTC-USD", 0.1, 0.1, 0.1, "neutral", 0.5, "G", 0.0),
        ],
        cash_symbol="USFR",
        cash_weight=0.2,
        gross_exposure=0.8,
        summary_text="s",
        implementation_text="i",
        signal_changes=[],
        as_of=None,
    )
    assert render_implementation(snap, []) is not None


def test_overview_benchmark_tile_branches(monkeypatch):
    from app.pages import overview as ov

    monkeypatch.setattr(ov, "_indicator_map", lambda _s: {})

    regime = KissRegime("goldilocks", 0.5, None, "up", "down", {"equity_trend": 0.1}, None, [])
    inds = [
        IndicatorSnapshot("SPY", None, None, None, None, "x", None, None),
        IndicatorSnapshot("QQQ", 100.0, 0.01, None, None, "x", None, None),
        IndicatorSnapshot("IWM", 100.0, 0.01, 0.02, None, "x", None, None),
        IndicatorSnapshot("XL", 100.0, None, None, None, "x", None, None),
    ]
    snap = RegimeOverviewSnapshot(
        regime=regime,
        regime_history=[],
        indicators=inds,
        confirmations=[],
        transitions=[SignalTransition("Regime", "a", "b", None, 1, "c")],
        as_of=None,
        summary_text="s",
    )
    assert render_regime_overview(snap, []) is not None
