import pandas as pd

from app.components.ui import allocation_band, fatal_error_page, macro_quadrant, make_table, sleeve_state_card, transition_strip
from app.config import load_config
from app.routing import _should_force_refresh
from app.models import (
    AlertFlag,
    ConfirmationSnapshot,
    IndicatorSnapshot,
    KissRegime,
    RegimeHistoryPoint,
    RegimeOverviewSnapshot,
    SignalChange,
    SignalTransition,
    SleeveAllocation,
    TickerDetailBundle,
    VamsSignal,
)
from app.pages.markets import render_markets
from app.pages.overview import render_regime_overview
from app.pages.ticker_detail import _mini_stat, render_ticker_detail
from app.pages.watchlist import render_watchlist
from app.models import MarketSnapshot, MarketIndexSnapshot, RatesSnapshot


def _regime_snapshot() -> RegimeOverviewSnapshot:
    regime = KissRegime(
        regime="goldilocks",
        regime_strength=0.42,
        hybrid_label=None,
        growth_direction="up",
        inflation_direction="down",
        component_scores={
            "equity_trend": 0.2,
            "cyclical_defensive_ratio": 0.1,
            "copper_gold_ratio": 0.3,
            "oil_trend": -0.1,
            "commodity_trend": -0.05,
            "yield_trend": -0.15,
        },
        as_of=None,
        reasons=["Growth proxies are trending up.", "Inflation proxies are trending down."],
    )
    return RegimeOverviewSnapshot(
        regime=regime,
        regime_history=[
            RegimeHistoryPoint(None, "reflation", 0.05, 0.08, 0.07),
            RegimeHistoryPoint(None, "goldilocks", 0.20, -0.10, 0.15),
        ],
        indicators=[
            IndicatorSnapshot("SPY", 500.0, 0.01, 0.03, 0.08, "above_50d", 0.15, None),
            IndicatorSnapshot("BTC-USD", 90000.0, 0.02, 0.05, 0.12, "above_50d", 0.45, None),
            IndicatorSnapshot("USO", 80.0, -0.01, -0.02, 0.04, "below_50d", 0.25, None),
            IndicatorSnapshot("DBC", 25.0, 0.01, 0.02, 0.06, "above_50d", 0.18, None),
            IndicatorSnapshot("GLD", 220.0, -0.01, -0.01, 0.02, "above_50d", 0.14, None),
            IndicatorSnapshot("QQQ", 450.0, 0.01, 0.04, 0.09, "above_50d", 0.17, None),
            IndicatorSnapshot("IWM", 210.0, 0.00, 0.02, 0.05, "above_50d", 0.22, None),
            IndicatorSnapshot("10Y", 0.043, None, 0.001, -0.002, "down", None, None),
            IndicatorSnapshot("10Y-5Y", 0.005, None, None, None, "steepening", None, None),
        ],
        confirmations=[
            ConfirmationSnapshot("SPY", "Equity confirmation", "bullish", 0.4, 0.2, 0.2, 0.15, SignalTransition("SPY", "neutral", "bullish", None, 3, "SPY changed neutral -> bullish 3 trading days ago."), None),
            ConfirmationSnapshot("AGG", "Bond confirmation", "neutral", 0.1, 0.05, 0.03, 0.12, SignalTransition("AGG", "neutral", "neutral", None, 8, "AGG has remained neutral for 8 trading days."), None),
            ConfirmationSnapshot("BTC-USD", "Risk appetite confirmation", "bullish", 0.5, 0.3, 0.25, 0.45, SignalTransition("BTC-USD", "neutral", "bullish", None, 2, "BTC-USD changed neutral -> bullish 2 trading days ago."), None),
        ],
        transitions=[
            SignalTransition("Regime", "reflation", "goldilocks", None, 1, "Regime changed reflation -> goldilocks 1 trading day ago."),
            SignalTransition("BTC-USD", "neutral", "bullish", None, 2, "BTC-USD changed neutral -> bullish 2 trading days ago."),
        ],
        as_of=None,
        summary_text="Goldilocks regime with growth up and inflation down.",
    )


def test_regime_overview_renders():
    cfg = load_config()
    layout = render_regime_overview(_regime_snapshot(), [], cfg)
    assert layout is not None
    body = layout.children[1].children[0]
    assert body.children[0].className == "overview-hero"
    assert body.children[1].className == "kpi-strip"
    assert body.children[2].className == "hero-grid"


def test_regime_overview_renders_with_empty_regime_history():
    cfg = load_config()
    snap = _regime_snapshot()
    snap = RegimeOverviewSnapshot(
        regime=snap.regime,
        regime_history=[],
        indicators=snap.indicators,
        confirmations=snap.confirmations,
        transitions=snap.transitions,
        as_of=snap.as_of,
        summary_text=snap.summary_text,
        warnings=snap.warnings,
    )
    layout = render_regime_overview(snap, [], cfg)
    assert layout is not None


def test_markets_page_renders():
    cfg = load_config()
    idx = MarketIndexSnapshot("SPY", 100.0, 0.01, 0.02, 0.05, 0.1, "above", "above", "above", None, None)
    market = MarketSnapshot(indices=[idx], positive_participation_ratio=0.5, as_of=None)
    rates = RatesSnapshot(None, 0.04, 0.045, 0.048, 0.005, 0.001, -0.002)
    sp = pd.DataFrame({"report_date": pd.to_datetime(["2020-01-01", "2021-01-01"]), "annual_returns": [0.1, 0.12]})
    layout = render_markets(market, rates, sp, [], cfg)
    assert layout is not None


def test_markets_page_no_indices_no_curve():
    cfg = load_config()
    market = MarketSnapshot(indices=[], positive_participation_ratio=0.0, as_of=None)
    rates = RatesSnapshot(None, None, None, None, None, None, None)
    sp = pd.DataFrame({"report_date": pd.to_datetime(["2020-01-01"]), "annual_returns": [0.1]})
    layout = render_markets(market, rates, sp, [], cfg)
    assert layout is not None


def test_ticker_detail_renders():
    cfg = load_config()
    bundle = TickerDetailBundle(
        symbol="SPY",
        info=pd.DataFrame({"symbol": ["SPY"], "sector": ["ETF"], "industry": ["Index Fund"]}),
        price=pd.DataFrame({"report_date": pd.to_datetime(["2024-12-31"]), "close": [200]}),
        valuation={"ttm_pe": pd.DataFrame({"report_date": pd.to_datetime(["2024-12-31"]), "ttm_pe": [30]})},
        quality={},
        growth={},
        news=pd.DataFrame({"title": ["Headline"]}),
        calendar=pd.DataFrame(),
        alerts=[AlertFlag("SPY", "allocation", "SPY regime confirmation is strong", "high")],
        errors=[],
        role_label="Equity confirmation",
        as_of=None,
    )
    layout = render_ticker_detail(bundle, cfg)
    assert layout is not None


def test_ticker_detail_empty_price_and_volume():
    cfg = load_config()
    dates = pd.date_range("2023-01-01", periods=260, freq="B")
    bundle = TickerDetailBundle(
        symbol="SPY",
        info=pd.DataFrame({"symbol": ["SPY"], "sector": ["ETF"], "industry": ["Index Fund"]}),
        price=pd.DataFrame({"report_date": dates, "close": range(260), "Volume": range(260)}),
        valuation={"ttm_pe": pd.DataFrame({"report_date": pd.to_datetime(["2024-12-31"]), "ttm_pe": [30]})},
        quality={"roe": pd.DataFrame({"report_date": pd.to_datetime(["2024-12-31"]), "roe": [0.25]})},
        growth={"revenue_yoy_growth": pd.DataFrame({"report_date": pd.to_datetime(["2024-12-31"]), "revenue_yoy_growth": [3.5]})},
        news=pd.DataFrame(),
        calendar=pd.DataFrame(),
        alerts=[],
        errors=[],
        role_label=None,
        as_of=None,
    )
    assert render_ticker_detail(bundle, cfg) is not None
    empty = TickerDetailBundle(
        symbol="X",
        info=pd.DataFrame({"symbol": ["X"]}),
        price=pd.DataFrame(),
        valuation={},
        quality={},
        growth={},
        news=pd.DataFrame(),
        calendar=pd.DataFrame(),
        alerts=[],
        errors=[],
        role_label=None,
        as_of=None,
    )
    assert render_ticker_detail(empty, cfg) is not None


def test_mini_stat_non_percent_branch():
    assert _mini_stat("x", 1.234, as_percent=False) is not None


def test_should_force_refresh_only_on_refresh_event():
    assert _should_force_refresh("refresh-state", {"refresh": 1}) is True
    assert _should_force_refresh("url", {"refresh": 1}) is False
    assert _should_force_refresh(None, {"refresh": 1}) is False


def test_fatal_error_page_renders():
    layout = fatal_error_page("Unable to load market data", ["boom"], ["Check the terminal logs."])
    assert layout is not None


def test_table_formats_numeric_values():
    table = make_table(pd.DataFrame({"return_1d": [0.0123], "close": [1234.567]}))
    assert table is not None


def test_allocation_band_renders():
    component = allocation_band([0.6, 0.3, 0.1], [0.6, 0.15, 0.1], [0.3, 0.3, 0.05], ["SPY", "AGG", "BTC-USD"])
    assert component is not None


def test_macro_quadrant_renders():
    component = macro_quadrant("goldilocks", 0.2, -0.1, None)
    assert component is not None


def test_sleeve_state_card_renders():
    allocation = SleeveAllocation("equity", "SPY", 0.6, 0.6, 0.3, "neutral", 0.5, "Goldilocks", None)
    signal = VamsSignal("SPY", "neutral", 0.1, 0.2, 0.15, 0.05, None, ["Mixed trend"])
    component = sleeve_state_card(allocation, signal)
    assert component is not None


def test_transition_strip_renders():
    component = transition_strip([SignalTransition("Regime", "reflation", "goldilocks", None, 1, "Regime changed yesterday.")])
    assert component is not None


def test_render_watchlist_empty_and_nonempty():
    cfg = load_config()
    empty = render_watchlist(pd.DataFrame(), [], cfg)
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
            "alert_count": [0],
            "alerts": [["a"]],
            "high_alert_count": [0],
        }
    )
    assert render_watchlist(df, ["warn"], cfg) is not None


def test_ticker_detail_mini_stat_formats():
    cfg = load_config()
    bundle = TickerDetailBundle(
        symbol="SPY",
        info=pd.DataFrame(),
        price=pd.DataFrame({"report_date": [pd.Timestamp("2024-01-01")], "close": [100.0]}),
        valuation={"ttm_pe": pd.DataFrame()},
        quality={"roe": pd.DataFrame({"report_date": [pd.Timestamp("2024-01-01")], "roe": [2.5]})},
        growth={"revenue_yoy_growth": pd.DataFrame()},
        news=pd.DataFrame(),
        calendar=pd.DataFrame(),
        alerts=[],
        errors=[],
        role_label=None,
        as_of=None,
    )
    assert render_ticker_detail(bundle, cfg) is not None


def test_overview_benchmark_tile_branches(monkeypatch):
    from app.pages import overview as ov

    monkeypatch.setattr(ov, "_indicator_map", lambda _s: {})
    cfg = load_config()

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
    assert render_regime_overview(snap, [], cfg) is not None
