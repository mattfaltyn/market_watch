from datetime import datetime

import pandas as pd

from app.models import DataResult
from app.services.watchlist_snapshot import build_watchlist_snapshot, get_ticker_detail
from tests.routing_fake import RoutingFakeClient


class FakeClient:
    def get_prices(self, symbol, force_refresh=False):
        return DataResult(
            pd.DataFrame(
                {
                    "report_date": pd.date_range("2024-01-01", periods=260, freq="B"),
                    "close": range(1, 261),
                }
            )
        )

    def get_beta(self, symbol, benchmark, force_refresh=False):
        return DataResult(pd.DataFrame({"report_date": [pd.Timestamp("2024-12-31")], "beta": [1.2]}))

    def get_calendar(self, symbol, force_refresh=False):
        return DataResult(pd.DataFrame({"earning_date": [pd.Timestamp.now(tz="UTC").normalize() + pd.Timedelta(days=7)]}))

    def get_news(self, symbol, force_refresh=False):
        return DataResult(pd.DataFrame({"publish_time": [pd.Timestamp.now(tz="UTC").normalize()], "title": ["note"]}))

    def get_metric_frame(self, symbol, method_name, ttl=None, force_refresh=False):
        mapping = {
            "ttm_pe": pd.DataFrame({"report_date": [pd.Timestamp("2024-12-31")], "ttm_pe": [25.0]}),
            "industry_ttm_pe": pd.DataFrame({"report_date": [pd.Timestamp("2024-12-31")], "industry_ttm_pe": [20.0]}),
            "quarterly_net_margin": pd.DataFrame({"report_date": [pd.Timestamp("2024-12-31")], "net_margin": [0.12]}),
            "quarterly_revenue_yoy_growth": pd.DataFrame({"report_date": [pd.Timestamp("2024-12-31")], "revenue_yoy_growth": [0.15]}),
        }
        return DataResult(mapping.get(method_name, pd.DataFrame()))

    def get_treasury_yields(self, force_refresh=False):
        return DataResult(
            pd.DataFrame(
                {
                    "report_date": pd.date_range("2024-01-01", periods=30, freq="B"),
                    "bc2_year": [0.04] * 30,
                    "bc10_year": [0.041] * 30,
                    "bc30_year": [0.045] * 30,
                }
            )
        )


def test_build_watchlist_snapshot_has_expected_columns():
    frame = build_watchlist_snapshot(FakeClient(), ["AAPL"], "SPY", {"large_move_1d": 0.01, "valuation_industry_gap": 0.2})
    assert {"symbol", "return_1d", "beta_1y", "alert_count", "recent_news_7d"}.issubset(frame.columns)
    assert frame.iloc[0]["symbol"] == "AAPL"


class _PlainDatetimePriceClient(RoutingFakeClient):
    """Price history max() is plain datetime (not pandas Timestamp) to cover as_of branch."""

    def get_prices(self, symbol, force_refresh=False):
        return DataResult(
            pd.DataFrame(
                {
                    "report_date": pd.Series([datetime(2024, 6, 1), datetime(2024, 6, 2)], dtype=object),
                    "close": [1.0, 2.0],
                }
            )
        )


def test_get_ticker_detail_as_of_plain_datetime_max():
    bundle = get_ticker_detail(_PlainDatetimePriceClient(), "AAPL", [], force_refresh=False)
    assert bundle.as_of == datetime(2024, 6, 2)


def test_get_ticker_detail_as_of_none_when_price_empty():
    class _EmptyPrice(RoutingFakeClient):
        def get_prices(self, symbol, force_refresh=False):
            return DataResult(pd.DataFrame())

    assert get_ticker_detail(_EmptyPrice(), "AAPL", [], force_refresh=False).as_of is None


def test_get_ticker_detail_as_of_none_when_no_report_date_column():
    class _NoDate(RoutingFakeClient):
        def get_prices(self, symbol, force_refresh=False):
            return DataResult(pd.DataFrame({"close": [1.0]}))

    assert get_ticker_detail(_NoDate(), "AAPL", [], force_refresh=False).as_of is None


def test_get_ticker_detail_as_of_none_when_report_dates_all_nat():
    class _AllNaT(RoutingFakeClient):
        def get_prices(self, symbol, force_refresh=False):
            return DataResult(pd.DataFrame({"report_date": [pd.NaT, pd.NaT], "close": [1.0, 2.0]}))

    assert get_ticker_detail(_AllNaT(), "AAPL", [], force_refresh=False).as_of is None
