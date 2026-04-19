"""Fake defeatbeta-shaped client for routing and integration-style tests."""

from __future__ import annotations

import pandas as pd

from app.models import DataResult


def price_frame(periods: int = 260, start: float = 100.0) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "report_date": pd.date_range("2024-01-01", periods=periods, freq="B"),
            "close": [start + i * 0.05 for i in range(periods)],
        }
    )


def treasury_frame(periods: int = 40) -> pd.DataFrame:
    dr = pd.date_range("2024-01-01", periods=periods, freq="B")
    return pd.DataFrame(
        {
            "report_date": dr,
            "bc2_year": [0.04 + i * 1e-4 for i in range(periods)],
            "bc10_year": [0.045 + i * 1e-4 for i in range(periods)],
            "bc30_year": [0.048 + i * 1e-4 for i in range(periods)],
        }
    )


class RoutingFakeClient:
    """Implements the subset of DefeatBetaClient used by dispatch_page and downstream services."""

    def __init__(self, boom: bool = False):
        self.boom = boom
        p = price_frame()
        y = treasury_frame()
        self.mapping = {
            "SPY": p,
            "AGG": p,
            "BTC-USD": p,
            "GLD": p,
            "USO": p,
            "DBC": p,
            "QQQ": p,
            "IWM": p,
            "XLY": p,
            "XLP": p,
            "CPER": p,
            "AAPL": p,
        }
        self.yields = y

    def get_prices(self, symbol, force_refresh=False):
        if self.boom:
            raise RuntimeError("simulated upstream failure")
        return DataResult(self.mapping[symbol])

    def last_price_source(self, symbol):
        return None

    def get_price_ratio_history(self, symbol_a, symbol_b, force_refresh=False):
        left = self.mapping[symbol_a][["report_date", "close"]].rename(columns={"close": "left"})
        right = self.mapping[symbol_b][["report_date", "close"]].rename(columns={"close": "right"})
        merged = left.merge(right, on="report_date")
        merged["ratio"] = merged["left"] / merged["right"]
        return DataResult(merged[["report_date", "ratio"]])

    def get_yield_series(self, force_refresh=False):
        return DataResult(self.yields)

    def get_treasury_yields(self, force_refresh=False):
        return DataResult(self.yields)

    def get_sp500_history(self, force_refresh=False):
        return DataResult(
            pd.DataFrame(
                {
                    "report_date": pd.date_range("2010-01-01", periods=5, freq="YE"),
                    "annual_returns": [0.12, 0.15, -0.05, 0.2, 0.1],
                }
            )
        )

    def get_beta(self, symbol, benchmark, force_refresh=False):
        return DataResult(pd.DataFrame({"report_date": [pd.Timestamp("2024-12-31")], "beta": [1.1]}))

    def get_calendar(self, symbol, force_refresh=False):
        return DataResult(pd.DataFrame({"earning_date": [pd.Timestamp.now(tz="UTC").normalize() + pd.Timedelta(days=10)]}))

    def get_news(self, symbol, force_refresh=False):
        return DataResult(pd.DataFrame({"publish_time": [pd.Timestamp.now(tz="UTC").normalize()], "title": ["n"], "publisher": ["p"], "source": ["s"]}))

    def get_filings(self, symbol, force_refresh=False):
        return DataResult(pd.DataFrame({"filing_date": [pd.Timestamp.now(tz="UTC").normalize()], "form_type": ["10-K"], "report_date": [pd.Timestamp.now(tz="UTC").normalize()]}))

    def get_transcripts(self, symbol, force_refresh=False):
        return DataResult(pd.DataFrame())

    def get_info(self, symbol, force_refresh=False):
        return DataResult(
            pd.DataFrame(
                {
                    "long_name": ["Test Co"],
                    "company_name": ["Test Co"],
                    "sector": ["Tech"],
                    "industry": ["Software"],
                }
            )
        )

    def get_metric_frame(self, symbol, method_name, ttl=None, force_refresh=False):
        templates = {
            "ttm_pe": pd.DataFrame({"report_date": [pd.Timestamp("2024-12-31")], "ttm_pe": [22.0]}),
            "industry_ttm_pe": pd.DataFrame({"report_date": [pd.Timestamp("2024-12-31")], "industry_ttm_pe": [20.0]}),
            "quarterly_net_margin": pd.DataFrame({"report_date": [pd.Timestamp("2024-12-31")], "net_margin": [0.1]}),
            "quarterly_revenue_yoy_growth": pd.DataFrame({"report_date": [pd.Timestamp("2024-12-31")], "revenue_yoy_growth": [0.05]}),
            "ps_ratio": pd.DataFrame(),
            "pb_ratio": pd.DataFrame(),
            "peg_ratio": pd.DataFrame(),
            "roe": pd.DataFrame({"report_date": [pd.Timestamp("2024-12-31")], "roe": [0.15]}),
            "roa": pd.DataFrame(),
            "roic": pd.DataFrame({"report_date": [pd.Timestamp("2024-12-31")], "roic": [0.12]}),
            "quarterly_operating_income_yoy_growth": pd.DataFrame(),
            "quarterly_eps_yoy_growth": pd.DataFrame({"report_date": [pd.Timestamp("2024-12-31")], "eps_yoy_growth": [0.08]}),
        }
        return DataResult(templates.get(method_name, pd.DataFrame()))

    def get_revenue_by_segment(self, symbol, force_refresh=False):
        return DataResult(pd.DataFrame({"report_date": [pd.Timestamp("2024-12-31")], "segment": ["A"], "revenue": [1.0]}))

    def get_revenue_by_geography(self, symbol, force_refresh=False):
        return DataResult(pd.DataFrame({"report_date": [pd.Timestamp("2024-12-31")], "region": ["US"], "revenue": [1.0]}))

    @staticmethod
    def latest_timestamp(frames):
        valid = [frame["report_date"].max() for frame in frames if not frame.empty and "report_date" in frame.columns]
        return max(valid).to_pydatetime() if valid else None
