import pandas as pd

from app.models import AlertFlag, MarketIndexSnapshot, MarketSnapshot, RatesSnapshot, RegimeSignal, TickerDetailBundle
from app.main import _should_force_refresh
from app.components.ui import fatal_error_page, make_table
from app.pages.overview import render_overview
from app.pages.ticker_detail import render_ticker_detail
from app.pages.watchlist import render_watchlist


def test_overview_renders():
    market = MarketSnapshot(
        indices=[MarketIndexSnapshot("SPY", 500.0, 0.01, 0.02, 0.03, 0.12, "above", "above", "above", None)],
        positive_participation_ratio=1.0,
        as_of=None,
    )
    rates = RatesSnapshot(None, 0.04, 0.042, 0.046, 0.002, 0.001, -0.001)
    regime = RegimeSignal("Neutral", 0, ["mixed conditions"])
    watchlist = pd.DataFrame({"symbol": ["AAPL"], "recent_news_7d": [2], "alert_count": [1], "high_alert_count": [0], "return_1d": [0.02]})
    layout = render_overview(market, rates, regime, watchlist, pd.DataFrame({"report_date": pd.to_datetime(["2024-12-31"]), "annual_returns": [0.2]}), [])
    assert layout is not None


def test_watchlist_renders():
    layout = render_watchlist(pd.DataFrame({"symbol": ["AAPL"], "alerts": [["test"]], "close": [100], "return_1d": [0.01], "return_5d": [0.02], "return_1m": [0.03], "beta_1y": [1.1], "days_to_earnings": [5], "ttm_pe": [20], "industry_ttm_pe": [18], "recent_news_7d": [2], "filing_count_30d": [1], "alert_count": [1], "high_alert_count": [0]}), [])
    assert layout is not None


def test_ticker_detail_renders():
    bundle = TickerDetailBundle(
        symbol="AAPL",
        info=pd.DataFrame({"symbol": ["AAPL"], "sector": ["Technology"], "industry": ["Consumer Electronics"]}),
        price=pd.DataFrame({"report_date": pd.to_datetime(["2024-12-31"]), "close": [200]}),
        valuation={"ttm_pe": pd.DataFrame({"report_date": pd.to_datetime(["2024-12-31"]), "ttm_pe": [30]})},
        quality={},
        growth={},
        news=pd.DataFrame({"title": ["Headline"]}),
        filings=pd.DataFrame({"form_type": ["10-K"]}),
        calendar=pd.DataFrame(),
        revenue_breakdown={"segment": pd.DataFrame(), "geography": pd.DataFrame()},
        transcripts=pd.DataFrame(),
        alerts=[AlertFlag("AAPL", "earnings", "Earnings in 3 days", "high")],
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
