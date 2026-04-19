import pandas as pd

from app.components.ui import fatal_error_page, make_table
from app.main import _should_force_refresh
from app.models import AlertFlag, KissPortfolioSnapshot, KissRegime, SignalChange, SleeveAllocation, TickerDetailBundle, VamsSignal
from app.pages.implementation import render_implementation
from app.pages.overview import render_kiss_overview
from app.pages.signals import render_signals
from app.pages.ticker_detail import render_ticker_detail


def _sample_snapshot() -> KissPortfolioSnapshot:
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


def test_kiss_overview_renders():
    layout = render_kiss_overview(_sample_snapshot(), [])
    assert layout is not None


def test_implementation_page_renders():
    layout = render_implementation(_sample_snapshot(), [])
    assert layout is not None


def test_signals_page_renders():
    regime = _sample_snapshot().regime
    vams_signals = {
        "SPY": VamsSignal("SPY", "neutral", 0.1, 0.2, 0.15, 0.05, None, ["Mixed trend"]),
        "AGG": VamsSignal("AGG", "bullish", 0.4, 0.1, 0.2, 0.2, None, ["Positive trend"]),
    }
    layout = render_signals(regime, vams_signals, [])
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
        alerts=[AlertFlag("SPY", "allocation", "SPY actual weight moved higher", "high")],
        errors=[],
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
