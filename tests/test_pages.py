import pandas as pd

from app.components.ui import allocation_band, fatal_error_page, macro_quadrant, make_table, sleeve_state_card, transition_strip
from app.routing import _should_force_refresh
from app.models import (
    AlertFlag,
    ConfirmationSnapshot,
    IndicatorSnapshot,
    KissPortfolioSnapshot,
    KissRegime,
    RegimeHistoryPoint,
    RegimeOverviewSnapshot,
    SignalChange,
    SignalTransition,
    SleeveAllocation,
    TickerDetailBundle,
    VamsSignal,
)
from app.pages.implementation import render_implementation
from app.pages.overview import render_regime_overview
from app.pages.signals import render_signals
from app.pages.ticker_detail import render_ticker_detail


def _portfolio_snapshot() -> KissPortfolioSnapshot:
    regime = KissRegime(
        regime="goldilocks",
        regime_strength=0.42,
        hybrid_label=None,
        growth_direction="up",
        inflation_direction="down",
        component_scores={"equity_trend": 0.2, "yield_trend": -0.1},
        as_of=None,
        reasons=["Growth proxies are trending up.", "Inflation proxies are trending down."],
    )
    return KissPortfolioSnapshot(
        regime=regime,
        sleeves=[
            SleeveAllocation("equity", "SPY", 0.6, 0.6, 0.3, "neutral", 0.5, "Goldilocks", 0.0),
            SleeveAllocation("fixed_income", "AGG", 0.3, 0.3, 0.3, "bullish", 1.0, "Goldilocks", 0.0),
            SleeveAllocation("bitcoin", "BTC-USD", 0.1, 0.1, 0.05, "neutral", 0.5, "Goldilocks", 0.05),
        ],
        cash_symbol="USFR",
        cash_weight=0.35,
        gross_exposure=0.65,
        summary_text="KISS is in Goldilocks with 65% gross exposure.",
        implementation_text="Set SPY to 30%, AGG to 30%, BTC-USD to 5%, hold USFR for the balance.",
        signal_changes=[SignalChange("BTC-USD", "actual_weight", "0.0%", "5.0%", "BTC-USD actual weight moved 0.0% -> 5.0%.")],
        as_of=None,
    )


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
            IndicatorSnapshot("10Y-2Y", 0.005, None, None, None, "steepening", None, None),
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
    layout = render_regime_overview(_regime_snapshot(), [])
    assert layout is not None


def test_implementation_page_renders():
    layout = render_implementation(_portfolio_snapshot(), [])
    assert layout is not None


def test_signals_page_renders():
    layout = render_signals(_regime_snapshot(), [])
    assert layout is not None


def test_ticker_detail_renders():
    bundle = TickerDetailBundle(
        symbol="SPY",
        info=pd.DataFrame({"symbol": ["SPY"], "sector": ["ETF"], "industry": ["Index Fund"]}),
        price=pd.DataFrame({"report_date": pd.to_datetime(["2024-12-31"]), "close": [200]}),
        valuation={"ttm_pe": pd.DataFrame({"report_date": pd.to_datetime(["2024-12-31"]), "ttm_pe": [30]})},
        quality={},
        growth={},
        news=pd.DataFrame({"title": ["Headline"]}),
        filings=pd.DataFrame({"form_type": ["10-K"]}),
        calendar=pd.DataFrame(),
        revenue_breakdown={"segment": pd.DataFrame(), "geography": pd.DataFrame()},
        transcripts=pd.DataFrame(),
        alerts=[AlertFlag("SPY", "allocation", "SPY regime confirmation is strong", "high")],
        errors=[],
        role_label="Equity confirmation",
    )
    layout = render_ticker_detail(bundle)
    assert layout is not None


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
    allocation = SleeveAllocation("equity", "SPY", 0.6, 0.6, 0.3, "neutral", 0.5, "Goldilocks", 0.0)
    signal = VamsSignal("SPY", "neutral", 0.1, 0.2, 0.15, 0.05, None, ["Mixed trend"])
    component = sleeve_state_card(allocation, signal)
    assert component is not None


def test_transition_strip_renders():
    component = transition_strip([SignalTransition("Regime", "reflation", "goldilocks", None, 1, "Regime changed yesterday.")])
    assert component is not None
