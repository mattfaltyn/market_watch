from __future__ import annotations

import builtins
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from app.data import yfinance_client as yfinance_mod
from app.data.cache import FileCache
from app.data.yfinance_client import (
    CachePolicy,
    MarketDataClient,
    YFinanceFetcher,
    fetch_prices_yfinance,
    _camel_to_snake,
    _info_to_frame,
)


class _ExplodingCache(FileCache):
    def get_or_set(self, key, factory, ttl_seconds=None, force_refresh=False):
        raise ValueError("cache boom")


def _sample_ohlcv(dr: pd.DatetimeIndex) -> pd.DataFrame:
    n = len(dr)
    return pd.DataFrame(
        {
            "Open": np.linspace(100, 100 + 0.5 * (n - 1), n),
            "Close": np.linspace(100.5, 100.5 + 0.5 * (n - 1), n),
            "High": np.linspace(101, 101 + 0.5 * (n - 1), n),
            "Low": np.linspace(99, 99 + 0.5 * (n - 1), n),
            "Volume": [1e6] * n,
        },
        index=dr,
    )


def test_fetch_prices_yfinance_returns_empty_when_import_fails(monkeypatch):
    sys.modules.pop("yfinance", None)
    real_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "yfinance":
            raise ImportError("missing")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    assert fetch_prices_yfinance("SPY").empty


def test_fetch_prices_yfinance_handles_ticker_exception(monkeypatch):
    import yfinance as yf

    class BadTicker:
        def __init__(self, symbol):
            pass

        def history(self, **kwargs):
            raise RuntimeError("network")

    monkeypatch.setattr(yf, "Ticker", BadTicker)
    assert fetch_prices_yfinance("SPY").empty


def test_yfinance_fetcher_class_delegates():
    f = YFinanceFetcher()
    assert f.fetch_prices("SPY") is not None


def test_fetch_prices_yfinance_empty_history_returns_empty(monkeypatch):
    import yfinance as yf

    class EmptyHistTicker:
        def __init__(self, symbol):
            pass

        def history(self, **kwargs):
            return pd.DataFrame()

    monkeypatch.setattr(yf, "Ticker", EmptyHistTicker)
    assert fetch_prices_yfinance("SPY").empty


def test_fetch_prices_yfinance_normalizes_columns(monkeypatch):
    import yfinance as yf

    dr = pd.date_range("2024-01-02", periods=3, freq="B")

    class OkTicker:
        def __init__(self, symbol):
            self.symbol = symbol

        def history(self, **kwargs):
            return pd.DataFrame(
                {
                    "Open": [100.0, 101.0, 102.0],
                    "Close": [100.5, 101.5, 102.5],
                    "High": [101.0, 102.0, 103.0],
                    "Low": [99.0, 100.0, 101.0],
                    "Volume": [1e6, 1e6, 1e6],
                },
                index=dr,
            )

    monkeypatch.setattr(yf, "Ticker", OkTicker)
    df = fetch_prices_yfinance("SPY")
    assert not df.empty
    assert set(df.columns) >= {"symbol", "report_date", "open", "close", "high", "low", "volume"}
    assert (df["symbol"] == "SPY").all()


def test_normalize_frame_none():
    assert MarketDataClient._normalize_frame(None).empty


def test_camel_to_snake():
    assert _camel_to_snake("trailingPE") == "trailing_pe"


def test_market_client_prices_returns_and_ratio(tmp_path: Path, monkeypatch):
    import yfinance as yf

    dr = pd.date_range("2024-01-02", periods=40, freq="B")

    class T:
        def __init__(self, symbol):
            self.symbol = str(symbol)

        def history(self, **kwargs):
            if self.symbol == "EMPTY":
                return pd.DataFrame()
            if self.symbol == "^GSPC":
                mdr = pd.date_range("2020-01-01", "2024-12-31", freq="ME")
                return _sample_ohlcv(mdr)
            if self.symbol in ("^FVX", "^TNX", "^TYX"):
                return pd.DataFrame({"Close": [4.0 + 0.1 * i for i in range(5)]}, index=dr[:5])
            return _sample_ohlcv(dr)

        @property
        def info(self):
            return {
                "trailingPE": 10.0,
                "priceToSalesTrailing12Months": 1.5,
                "priceToBook": 2.0,
                "pegRatio": 1.2,
                "returnOnEquity": 0.15,
                "returnOnAssets": 0.06,
                "beta": 1.0,
                "longName": "Co",
            }

        @property
        def news(self):
            return [{"title": "t", "publisher": "p", "providerPublishTime": 1_700_000_000}]

        @property
        def calendar(self):
            return {"Earnings Date": np.array([pd.Timestamp("2025-06-01", tz="UTC")])}

        @property
        def quarterly_income_stmt(self):
            cols = pd.to_datetime(
                ["2023-03-31", "2023-06-30", "2023-09-30", "2023-12-31", "2024-03-31", "2024-06-30"]
            )
            data = {
                cols[0]: [100.0, 25.0, 15.0, 1.0],
                cols[1]: [110.0, 27.0, 16.0, 1.1],
                cols[2]: [120.0, 29.0, 17.0, 1.2],
                cols[3]: [130.0, 31.0, 18.0, 1.3],
                cols[4]: [140.0, 33.0, 19.0, 1.4],
                cols[5]: [150.0, 35.0, 20.0, 1.5],
            }
            return pd.DataFrame(data, index=["Total Revenue", "Operating Income", "Net Income", "Basic EPS"])

    monkeypatch.setattr(yf, "Ticker", T)
    cache = FileCache(tmp_path, default_ttl_seconds=60)
    c = MarketDataClient(cache, policy=CachePolicy())

    r = c.get_prices("SPY")
    assert not r.data.empty
    assert c.last_price_source("SPY") == "yfinance"

    rs = c.get_return_series("SPY", [1, 5])
    assert "return_1d" in rs.data.columns

    pr = c.get_price_ratio_history("SPY", "QQQ")
    assert not pr.data.empty

    y = c.get_treasury_yields()
    assert not y.data.empty and "bc10_year" in y.data.columns

    sp = c.get_sp500_history()
    assert not sp.data.empty

    assert not c.get_info("SPY").data.empty
    assert not c.get_news("SPY").data.empty
    assert not c.get_calendar("SPY").data.empty
    assert not c.get_beta("SPY", "SPY").data.empty

    for m in ("ttm_pe", "ps_ratio", "pb_ratio", "peg_ratio", "roe", "roa", "roic"):
        assert not c.get_metric_frame("SPY", m).data.empty
    assert not c.get_metric_frame("SPY", "quarterly_net_margin").data.empty
    assert not c.get_metric_frame("SPY", "quarterly_revenue_yoy_growth").data.empty
    assert not c.get_metric_frame("SPY", "quarterly_operating_income_yoy_growth").data.empty
    assert not c.get_metric_frame("SPY", "quarterly_eps_yoy_growth").data.empty
    assert c.get_metric_frame("SPY", "industry_ttm_pe").data.empty

    bad = c.get_metric_frame("SPY", "unknown_metric_xyz")
    assert bad.data.empty and bad.errors

    re = c.get_prices("EMPTY")
    assert re.data.empty
    assert c.last_price_source("EMPTY") is None

    left = c.get_price_ratio_history("EMPTY", "SPY")
    assert left.data.empty


def test_market_client_cache_error(monkeypatch, tmp_path: Path):
    import yfinance as yf

    dr = pd.date_range("2024-01-02", periods=5, freq="B")

    class T:
        def __init__(self, symbol):
            pass

        def history(self, **kwargs):
            return _sample_ohlcv(dr)

    monkeypatch.setattr(yf, "Ticker", T)
    c = MarketDataClient(_ExplodingCache(tmp_path, default_ttl_seconds=60), policy=CachePolicy())
    out = c.get_prices("ZZZ")
    assert out.data.empty
    assert "cache boom" in out.errors[0]


def test_latest_timestamp_branches():
    assert MarketDataClient.latest_timestamp([]) is None
    assert MarketDataClient.latest_timestamp([pd.DataFrame()]) is None
    ts = MarketDataClient.latest_timestamp([pd.DataFrame({"report_date": [pd.Timestamp("2024-01-10")]})])
    assert ts is not None


def test_get_metric_frame_scalar_metrics_populated(monkeypatch, tmp_path: Path):
    import yfinance as yf

    class T:
        def __init__(self, symbol):
            pass

        def history(self, **kwargs):
            return pd.DataFrame()

        @property
        def info(self):
            return {
                "trailingPE": 12.0,
                "priceToSalesTrailing12Months": 1.2,
                "priceToBook": 2.2,
                "pegRatio": 1.1,
                "returnOnEquity": 0.11,
                "returnOnAssets": 0.05,
            }

    monkeypatch.setattr(yf, "Ticker", T)
    c = MarketDataClient(FileCache(tmp_path, default_ttl_seconds=60), policy=CachePolicy())
    for m in ("ps_ratio", "pb_ratio", "peg_ratio", "roe", "roa", "roic"):
        assert not c.get_metric_frame("X", m).data.empty


def test_get_beta_empty_when_no_beta(monkeypatch, tmp_path: Path):
    import yfinance as yf

    class T:
        def __init__(self, symbol):
            pass

        def history(self, **kwargs):
            return pd.DataFrame()

        @property
        def info(self):
            return {"longName": "No Beta"}

    monkeypatch.setattr(yf, "Ticker", T)
    c = MarketDataClient(FileCache(tmp_path, default_ttl_seconds=60), policy=CachePolicy())
    assert c.get_beta("Z", "SPY").data.empty


def test_get_info_and_news_empty(monkeypatch, tmp_path: Path):
    import yfinance as yf

    class T:
        def __init__(self, symbol):
            self.symbol = symbol

        def history(self, **kwargs):
            return pd.DataFrame()

        @property
        def info(self):
            return {} if self.symbol == "E" else {"trailingPE": 1.0}

        @property
        def news(self):
            if self.symbol == "N1":
                return None
            if self.symbol == "N2":
                return [{"title": "x"}]  # no providerPublishTime
            if self.symbol == "N3":
                return ["bad"]
            return []

    monkeypatch.setattr(yf, "Ticker", T)
    c = MarketDataClient(FileCache(tmp_path, default_ttl_seconds=60), policy=CachePolicy())
    assert c.get_info("E").data.empty
    assert c.get_news("N1").data.empty
    n2 = c.get_news("N2")
    assert not n2.data.empty
    assert c.get_news("N3").data.empty
    assert c.get_news("NX").data.empty


def test_calendar_branches(monkeypatch, tmp_path: Path):
    import yfinance as yf

    class TCal:
        def __init__(self, symbol):
            self.symbol = str(symbol)

        def history(self, **kwargs):
            return pd.DataFrame()

        @property
        def info(self):
            return {}

        @property
        def calendar(self):
            if self.symbol == "D1":
                return {"Wrong": [1]}
            if self.symbol == "D2":
                return pd.DataFrame({"foo": [1]})
            if self.symbol == "D3":
                return pd.DataFrame()
            return {"Earnings Date": pd.Timestamp("2025-01-01")}

    monkeypatch.setattr(yf, "Ticker", TCal)
    c = MarketDataClient(FileCache(tmp_path, default_ttl_seconds=60), policy=CachePolicy())
    assert c.get_calendar("D1").data.empty
    assert not c.get_calendar("D2").data.empty
    assert c.get_calendar("D3").data.empty
    assert not c.get_calendar("OK").data.empty


def test_treasury_partial_failure(monkeypatch, tmp_path: Path):
    import yfinance as yf

    class T:
        def __init__(self, symbol):
            self.symbol = str(symbol)

        def history(self, **kwargs):
            dr = pd.date_range("2024-01-02", periods=3, freq="B")
            if self.symbol == "^FVX":
                raise RuntimeError("boom")
            return pd.DataFrame({"Close": [5.0, 5.1, 5.2]}, index=dr)

    monkeypatch.setattr(yf, "Ticker", T)
    c = MarketDataClient(FileCache(tmp_path, default_ttl_seconds=60), policy=CachePolicy())
    y = c.get_treasury_yields()
    assert not y.data.empty


def test_treasury_all_fail(monkeypatch, tmp_path: Path):
    import yfinance as yf

    class T:
        def __init__(self, symbol):
            pass

        def history(self, **kwargs):
            return pd.DataFrame()

    monkeypatch.setattr(yf, "Ticker", T)
    c = MarketDataClient(FileCache(tmp_path, default_ttl_seconds=60), policy=CachePolicy())
    assert c.get_treasury_yields().data.empty


def test_sp500_empty_history(monkeypatch, tmp_path: Path):
    import yfinance as yf

    class T:
        def __init__(self, symbol):
            pass

        def history(self, **kwargs):
            return pd.DataFrame()

    monkeypatch.setattr(yf, "Ticker", T)
    c = MarketDataClient(FileCache(tmp_path, default_ttl_seconds=60), policy=CachePolicy())
    assert c.get_sp500_history().data.empty


def test_quarterly_frames_short_or_missing(monkeypatch, tmp_path: Path):
    import yfinance as yf

    class T:
        def __init__(self, symbol):
            pass

        def history(self, **kwargs):
            return pd.DataFrame()

        @property
        def info(self):
            return {}

        @property
        def quarterly_income_stmt(self):
            cols = pd.to_datetime(["2023-03-31", "2023-06-30"])
            return pd.DataFrame(
                {cols[0]: [100.0, 20.0], cols[1]: [110.0, 22.0]},
                index=["Total Revenue", "Operating Income"],
            )

    monkeypatch.setattr(yf, "Ticker", T)
    c = MarketDataClient(FileCache(tmp_path, default_ttl_seconds=60), policy=CachePolicy())
    assert c.get_metric_frame("Q", "quarterly_revenue_yoy_growth").data.empty
    assert c.get_metric_frame("Q", "quarterly_net_margin").data.empty


def test_quarterly_net_margin_no_net_income_row(monkeypatch, tmp_path: Path):
    import yfinance as yf

    class T:
        def __init__(self, symbol):
            pass

        def history(self, **kwargs):
            return pd.DataFrame()

        @property
        def quarterly_income_stmt(self):
            cols = pd.to_datetime(["2023-03-31", "2023-06-30", "2023-09-30", "2023-12-31", "2024-03-31"])
            return pd.DataFrame(
                {c: [100.0 + i, 1.0] for i, c in enumerate(cols)},
                index=["Total Revenue", "Other"],
            )

    monkeypatch.setattr(yf, "Ticker", T)
    c = MarketDataClient(FileCache(tmp_path, default_ttl_seconds=60), policy=CachePolicy())
    assert c.get_metric_frame("Q", "quarterly_net_margin").data.empty


def test_row_by_labels_substring_match(monkeypatch, tmp_path: Path):
    import yfinance as yf

    class T:
        def __init__(self, symbol):
            pass

        def history(self, **kwargs):
            return pd.DataFrame()

        @property
        def quarterly_income_stmt(self):
            cols = pd.to_datetime(
                ["2023-03-31", "2023-06-30", "2023-09-30", "2023-12-31", "2024-03-31", "2024-06-30"]
            )
            data = {c: [100.0 + float(i), 10.0 + float(i), 2.0] for i, c in enumerate(cols)}
            return pd.DataFrame(data, index=["Something Revenue Total", "Operating Income X", "Basic EPS"])

    monkeypatch.setattr(yf, "Ticker", T)
    c = MarketDataClient(FileCache(tmp_path, default_ttl_seconds=60), policy=CachePolicy())
    assert not c.get_metric_frame("Q", "quarterly_revenue_yoy_growth").data.empty


def test_get_yield_series_alias(tmp_path: Path, monkeypatch):
    import yfinance as yf

    dr = pd.date_range("2024-01-02", periods=3, freq="B")

    class T:
        def __init__(self, symbol):
            pass

        def history(self, **kwargs):
            return pd.DataFrame({"Close": [4.0, 4.1, 4.2]}, index=dr)

    monkeypatch.setattr(yf, "Ticker", T)
    c = MarketDataClient(FileCache(tmp_path, default_ttl_seconds=60), policy=CachePolicy())
    g = c.get_yield_series()
    assert not g.data.empty


def test_sp500_hist_exception(monkeypatch, tmp_path: Path):
    import yfinance as yf

    class T:
        def __init__(self, symbol):
            pass

        def history(self, **kwargs):
            raise OSError("x")

    monkeypatch.setattr(yf, "Ticker", T)
    c = MarketDataClient(FileCache(tmp_path, default_ttl_seconds=60), policy=CachePolicy())
    assert c.get_sp500_history().data.empty


def test_info_loader_exception(monkeypatch, tmp_path: Path):
    import yfinance as yf

    class T:
        def __init__(self, symbol):
            pass

        def history(self, **kwargs):
            return pd.DataFrame()

        @property
        def info(self):
            raise RuntimeError("nope")

    monkeypatch.setattr(yf, "Ticker", T)
    c = MarketDataClient(FileCache(tmp_path, default_ttl_seconds=60), policy=CachePolicy())
    assert c.get_info("Z").data.empty


def test_info_to_frame_variants():
    assert _info_to_frame(None).empty
    assert _info_to_frame({}).empty
    assert _info_to_frame({"nested": {"a": 1}}).empty
    assert not _info_to_frame({"longName": "X"}).empty


def test_import_yfinance_none_branches(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(yfinance_mod, "_import_yfinance", lambda: None)
    c = MarketDataClient(FileCache(tmp_path, default_ttl_seconds=60), policy=CachePolicy())
    assert c.get_treasury_yields().data.empty
    assert c.get_sp500_history().data.empty
    assert c.get_prices("SPY").data.empty
    assert c.get_info("SPY").data.empty
    assert c.get_news("SPY").data.empty
    assert c.get_calendar("SPY").data.empty


def test_get_return_series_empty_prices(monkeypatch, tmp_path: Path):
    import yfinance as yf

    class T:
        def __init__(self, symbol):
            pass

        def history(self, **kwargs):
            return pd.DataFrame()

    monkeypatch.setattr(yf, "Ticker", T)
    c = MarketDataClient(FileCache(tmp_path, default_ttl_seconds=60), policy=CachePolicy())
    assert c.get_return_series("Z", [1, 2]).data.empty


def test_price_ratio_non_overlapping_dates(monkeypatch, tmp_path: Path):
    import yfinance as yf

    class T:
        def __init__(self, symbol):
            self.symbol = str(symbol)

        def history(self, **kwargs):
            if self.symbol == "A":
                return pd.DataFrame({"Close": [1.0]}, index=[pd.Timestamp("2020-01-02")])
            return pd.DataFrame({"Close": [2.0]}, index=[pd.Timestamp("2021-01-02")])

    monkeypatch.setattr(yf, "Ticker", T)
    c = MarketDataClient(FileCache(tmp_path, default_ttl_seconds=60), policy=CachePolicy())
    assert c.get_price_ratio_history("A", "B").data.empty


def test_price_ratio_all_nan_ratio_dropped(monkeypatch, tmp_path: Path):
    import yfinance as yf

    dr = pd.Timestamp("2024-01-02")

    class T:
        def __init__(self, symbol):
            self.symbol = str(symbol)

        def history(self, **kwargs):
            if self.symbol == "A":
                return pd.DataFrame({"Close": [float("nan")]}, index=[dr])
            return pd.DataFrame({"Close": [2.0]}, index=[dr])

    monkeypatch.setattr(yf, "Ticker", T)
    c = MarketDataClient(FileCache(tmp_path, default_ttl_seconds=60), policy=CachePolicy())
    assert c.get_price_ratio_history("A", "B").data.empty


def test_sp500_missing_close_and_all_nan(monkeypatch, tmp_path: Path):
    import yfinance as yf

    class TNoClose:
        def __init__(self, symbol):
            pass

        def history(self, **kwargs):
            return pd.DataFrame({"Open": [100.0]}, index=[pd.Timestamp("2020-06-01")])

    monkeypatch.setattr(yf, "Ticker", TNoClose)
    c = MarketDataClient(FileCache(tmp_path, default_ttl_seconds=60), policy=CachePolicy())
    assert c.get_sp500_history().data.empty

    class TNaN:
        def __init__(self, symbol):
            pass

        def history(self, **kwargs):
            return pd.DataFrame({"Close": [float("nan")]}, index=[pd.Timestamp("2020-06-01")])

    monkeypatch.setattr(yf, "Ticker", TNaN)
    c2 = MarketDataClient(FileCache(tmp_path / "b", default_ttl_seconds=60), policy=CachePolicy())
    assert c2.get_sp500_history().data.empty


def test_sp500_tz_aware_index(monkeypatch, tmp_path: Path):
    import yfinance as yf

    idx = pd.date_range("2020-01-01", periods=24, freq="ME", tz="UTC")

    class T:
        def __init__(self, symbol):
            pass

        def history(self, **kwargs):
            return pd.DataFrame({"Close": np.linspace(100, 120, len(idx))}, index=idx)

    monkeypatch.setattr(yf, "Ticker", T)
    c = MarketDataClient(FileCache(tmp_path, default_ttl_seconds=60), policy=CachePolicy())
    assert not c.get_sp500_history().data.empty


def test_load_info_not_dict(monkeypatch, tmp_path: Path):
    import yfinance as yf

    class T:
        def __init__(self, symbol):
            pass

        def history(self, **kwargs):
            return pd.DataFrame()

        @property
        def info(self):
            return []

    monkeypatch.setattr(yf, "Ticker", T)
    c = MarketDataClient(FileCache(tmp_path, default_ttl_seconds=60), policy=CachePolicy())
    assert c.get_info("Z").data.empty


def test_news_calendar_exceptions(monkeypatch, tmp_path: Path):
    import yfinance as yf

    class TN:
        def __init__(self, symbol):
            pass

        def history(self, **kwargs):
            return pd.DataFrame()

        @property
        def news(self):
            raise RuntimeError("no news")

    monkeypatch.setattr(yf, "Ticker", TN)
    c = MarketDataClient(FileCache(tmp_path, default_ttl_seconds=60), policy=CachePolicy())
    assert c.get_news("Z").data.empty

    class TC:
        def __init__(self, symbol):
            self.symbol = str(symbol)

        def history(self, **kwargs):
            return pd.DataFrame()

        @property
        def calendar(self):
            if self.symbol == "E":
                raise RuntimeError("cal")
            if self.symbol == "N":
                return None
            return 42

    monkeypatch.setattr(yf, "Ticker", TC)
    c2 = MarketDataClient(FileCache(tmp_path / "c2", default_ttl_seconds=60), policy=CachePolicy())
    assert c2.get_calendar("E").data.empty
    assert c2.get_calendar("N").data.empty
    assert c2.get_calendar("X").data.empty


def test_calendar_dataframe_earningdate_column(monkeypatch, tmp_path: Path):
    import yfinance as yf

    class T:
        def __init__(self, symbol):
            self.symbol = str(symbol)

        def history(self, **kwargs):
            return pd.DataFrame()

        @property
        def calendar(self):
            if self.symbol == "E2":
                return pd.DataFrame({"Earnings Date": [pd.Timestamp("2025-04-01", tz="UTC")]})
            return pd.DataFrame({"earningDate": [pd.Timestamp("2025-04-01", tz="UTC")]})

    monkeypatch.setattr(yf, "Ticker", T)
    c = MarketDataClient(FileCache(tmp_path, default_ttl_seconds=60), policy=CachePolicy())
    assert not c.get_calendar("Z").data.empty
    assert not c.get_calendar("E2").data.empty


def test_treasury_close_all_nan_dropped(monkeypatch, tmp_path: Path):
    import yfinance as yf

    dr = pd.date_range("2024-01-02", periods=2, freq="B")

    class T:
        def __init__(self, symbol):
            pass

        def history(self, **kwargs):
            return pd.DataFrame({"Close": [float("nan"), float("nan")]}, index=dr)

    monkeypatch.setattr(yf, "Ticker", T)
    c = MarketDataClient(FileCache(tmp_path, default_ttl_seconds=60), policy=CachePolicy())
    assert c.get_treasury_yields().data.empty


def test_treasury_missing_close_and_empty_slice(monkeypatch, tmp_path: Path):
    import yfinance as yf

    class T:
        def __init__(self, symbol):
            self.symbol = str(symbol)

        def history(self, **kwargs):
            if "^" in self.symbol:
                return pd.DataFrame({"Open": [1.0]}, index=[pd.Timestamp("2024-01-02")])
            return pd.DataFrame()

    monkeypatch.setattr(yf, "Ticker", T)
    c = MarketDataClient(FileCache(tmp_path, default_ttl_seconds=60), policy=CachePolicy())
    assert c.get_treasury_yields().data.empty


def test_treasury_history_exception(monkeypatch, tmp_path: Path):
    import yfinance as yf

    class T:
        def __init__(self, symbol):
            pass

        def history(self, **kwargs):
            raise OSError("fail")

    monkeypatch.setattr(yf, "Ticker", T)
    c = MarketDataClient(FileCache(tmp_path, default_ttl_seconds=60), policy=CachePolicy())
    assert c.get_treasury_yields().data.empty


def test_quarterly_income_stmt_none_or_empty(monkeypatch, tmp_path: Path):
    import yfinance as yf

    class TNone:
        def __init__(self, symbol):
            pass

        def history(self, **kwargs):
            return pd.DataFrame()

        @property
        def quarterly_income_stmt(self):
            return None

    monkeypatch.setattr(yf, "Ticker", TNone)
    c = MarketDataClient(FileCache(tmp_path, default_ttl_seconds=60), policy=CachePolicy())
    assert c.get_metric_frame("Q", "quarterly_net_margin").data.empty

    class TEmpty:
        def __init__(self, symbol):
            pass

        def history(self, **kwargs):
            return pd.DataFrame()

        @property
        def quarterly_income_stmt(self):
            return pd.DataFrame()

    monkeypatch.setattr(yf, "Ticker", TEmpty)
    c2 = MarketDataClient(FileCache(tmp_path / "mt", default_ttl_seconds=60), policy=CachePolicy())
    assert c2.get_metric_frame("Q", "quarterly_revenue_yoy_growth").data.empty


def test_quarterly_stmt_exception_and_import_none(monkeypatch, tmp_path: Path):
    import yfinance as yf

    class T:
        def __init__(self, symbol):
            pass

        def history(self, **kwargs):
            return pd.DataFrame()

        @property
        def quarterly_income_stmt(self):
            raise ValueError("no stmt")

    monkeypatch.setattr(yf, "Ticker", T)
    c = MarketDataClient(FileCache(tmp_path, default_ttl_seconds=60), policy=CachePolicy())
    assert c.get_metric_frame("Q", "quarterly_net_margin").data.empty
    assert c.get_metric_frame("Q", "quarterly_revenue_yoy_growth").data.empty

    monkeypatch.setattr(yfinance_mod, "_import_yfinance", lambda: None)
    c2 = MarketDataClient(FileCache(tmp_path / "q2", default_ttl_seconds=60), policy=CachePolicy())
    assert c2._quarterly_net_margin_frame("x").empty
    assert c2._quarterly_yoy_frame("x", ("Total Revenue",), "c").empty


def test_row_by_labels_exact_match_first_loop(monkeypatch, tmp_path: Path):
    import yfinance as yf

    class T:
        def __init__(self, symbol):
            pass

        def history(self, **kwargs):
            return pd.DataFrame()

        @property
        def quarterly_income_stmt(self):
            cols = pd.to_datetime(
                ["2023-03-31", "2023-06-30", "2023-09-30", "2023-12-31", "2024-03-31", "2024-06-30"]
            )
            return pd.DataFrame({cols[i]: [100.0 + float(i)] for i in range(6)}, index=["Total Revenue"])

    monkeypatch.setattr(yf, "Ticker", T)
    c = MarketDataClient(FileCache(tmp_path, default_ttl_seconds=60), policy=CachePolicy())
    assert not c.get_metric_frame("Q", "quarterly_revenue_yoy_growth").data.empty


def test_quarterly_yoy_row_not_found(monkeypatch, tmp_path: Path):
    import yfinance as yf

    class T:
        def __init__(self, symbol):
            pass

        def history(self, **kwargs):
            return pd.DataFrame()

        @property
        def quarterly_income_stmt(self):
            cols = pd.to_datetime(
                ["2023-03-31", "2023-06-30", "2023-09-30", "2023-12-31", "2024-03-31", "2024-06-30"]
            )
            return pd.DataFrame({c: [100.0] for c in cols}, index=["Unrelated Row Name"])

    monkeypatch.setattr(yf, "Ticker", T)
    c = MarketDataClient(FileCache(tmp_path, default_ttl_seconds=60), policy=CachePolicy())
    assert c.get_metric_frame("Q", "quarterly_revenue_yoy_growth").data.empty


def test_scalar_metric_empty_info_frame(monkeypatch, tmp_path: Path):
    import yfinance as yf

    class T:
        def __init__(self, symbol):
            pass

        def history(self, **kwargs):
            return pd.DataFrame()

        @property
        def info(self):
            return None

    monkeypatch.setattr(yf, "Ticker", T)
    c = MarketDataClient(FileCache(tmp_path, default_ttl_seconds=60), policy=CachePolicy())
    assert c.get_metric_frame("Z", "ttm_pe").data.empty


def test_scalar_metric_val_none_branch(monkeypatch, tmp_path: Path):
    import yfinance as yf

    class T:
        def __init__(self, symbol):
            pass

        def history(self, **kwargs):
            return pd.DataFrame()

        @property
        def info(self):
            return {"trailingPE": float("nan")}

    monkeypatch.setattr(yf, "Ticker", T)
    c = MarketDataClient(FileCache(tmp_path, default_ttl_seconds=60), policy=CachePolicy())
    assert c.get_metric_frame("Z", "ttm_pe").data.empty


def test_quarterly_yoy_all_nan_yoy_dropped(monkeypatch, tmp_path: Path):
    import yfinance as yf

    class T:
        def __init__(self, symbol):
            pass

        def history(self, **kwargs):
            return pd.DataFrame()

        @property
        def quarterly_income_stmt(self):
            cols = pd.to_datetime(
                ["2023-03-31", "2023-06-30", "2023-09-30", "2023-12-31", "2024-03-31"]
            )
            vals = [1.0, float("nan"), float("nan"), float("nan"), float("nan")]
            return pd.DataFrame({c: [vals[i]] for i, c in enumerate(cols)}, index=["Total Revenue"])

    monkeypatch.setattr(yf, "Ticker", T)
    c = MarketDataClient(FileCache(tmp_path, default_ttl_seconds=60), policy=CachePolicy())
    assert c.get_metric_frame("Q", "quarterly_revenue_yoy_growth").data.empty


def test_get_beta_empty_info_frame(monkeypatch, tmp_path: Path):
    import yfinance as yf

    class T:
        def __init__(self, symbol):
            pass

        def history(self, **kwargs):
            return pd.DataFrame()

        @property
        def info(self):
            return {}

    monkeypatch.setattr(yf, "Ticker", T)
    c = MarketDataClient(FileCache(tmp_path, default_ttl_seconds=60), policy=CachePolicy())
    assert c.get_beta("Z", "SPY").data.empty


def test_get_beta_beta3year_key(monkeypatch, tmp_path: Path):
    import yfinance as yf

    class T:
        def __init__(self, symbol):
            pass

        def history(self, **kwargs):
            return pd.DataFrame()

        @property
        def info(self):
            return {"beta3Year": 0.9}

    monkeypatch.setattr(yf, "Ticker", T)
    c = MarketDataClient(FileCache(tmp_path, default_ttl_seconds=60), policy=CachePolicy())
    b = c.get_beta("Z", "SPY")
    assert not b.data.empty
    assert abs(float(b.data.iloc[0]["beta"]) - 0.9) < 1e-6


def test_scalar_metric_missing_column(monkeypatch, tmp_path: Path):
    import yfinance as yf

    class T:
        def __init__(self, symbol):
            pass

        def history(self, **kwargs):
            return pd.DataFrame()

        @property
        def info(self):
            return {"longName": "only"}

    monkeypatch.setattr(yf, "Ticker", T)
    c = MarketDataClient(FileCache(tmp_path, default_ttl_seconds=60), policy=CachePolicy())
    assert c.get_metric_frame("Z", "ttm_pe").data.empty


def test_net_margin_skips_zero_revenue(monkeypatch, tmp_path: Path):
    import yfinance as yf

    class T:
        def __init__(self, symbol):
            pass

        def history(self, **kwargs):
            return pd.DataFrame()

        @property
        def quarterly_income_stmt(self):
            c = pd.to_datetime(["2023-03-31", "2023-06-30", "2023-09-30", "2023-12-31", "2024-03-31"])
            return pd.DataFrame(
                {c[0]: [0.0, 1.0], c[1]: [100.0, 10.0], c[2]: [100.0, 10.0], c[3]: [100.0, 10.0], c[4]: [100.0, 10.0]},
                index=["Total Revenue", "Net Income"],
            )

    monkeypatch.setattr(yf, "Ticker", T)
    c = MarketDataClient(FileCache(tmp_path, default_ttl_seconds=60), policy=CachePolicy())
    df = c.get_metric_frame("Q", "quarterly_net_margin").data
    assert df.empty or (df["net_margin"] > 0).all()
