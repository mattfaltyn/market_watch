from __future__ import annotations

import builtins
from pathlib import Path

import pandas as pd
import pytest

from app.data.cache import FileCache
from app.data.defeatbeta_client import CachePolicy, DefeatBetaClient


class _ExplodingCache(FileCache):
    def get_or_set(self, key, factory, ttl_seconds=None, force_refresh=False):
        raise ValueError("cache boom")


class _News:
    def get_all_news(self):
        return pd.DataFrame(
            {"report_date": [pd.Timestamp("2024-06-01")], "publish_time": [pd.Timestamp("2024-06-01")], "title": ["t"]}
        )


class _Transcripts:
    def get_transcripts_list(self):
        return pd.DataFrame({"report_date": [pd.Timestamp("2024-06-01")], "earnings_date": [pd.Timestamp("2024-06-01")]})


class FakeTicker:
    def __init__(self, symbol: str):
        self.symbol = symbol
        self._df = pd.DataFrame(
            {"report_date": pd.date_range("2024-01-01", periods=40, freq="B"), "close": [100.0 + i for i in range(40)]}
        )

    def price(self):
        return self._df

    def beta(self, period="1y", benchmark="SPY"):
        return pd.DataFrame({"report_date": [pd.Timestamp("2024-12-31")], "beta": [1.05]})

    def calendar(self):
        return pd.DataFrame({"earning_date": [pd.Timestamp("2025-01-01")]})

    def info(self):
        return pd.DataFrame({"symbol": [self.symbol]})

    def news(self):
        return _News()

    def sec_filing(self):
        return pd.DataFrame({"filing_date": [pd.Timestamp("2024-12-01")], "form_type": ["10-Q"], "report_date": [pd.Timestamp("2024-12-01")]})

    def earning_call_transcripts(self):
        return _Transcripts()

    def revenue_by_segment(self):
        return pd.DataFrame({"report_date": [pd.Timestamp("2024-12-01")], "segment": ["A"], "revenue": [1.0]})

    def revenue_by_geography(self):
        return pd.DataFrame({"report_date": [pd.Timestamp("2024-12-01")], "region": ["US"], "revenue": [1.0]})

    def ttm_pe(self):
        return pd.DataFrame({"report_date": [pd.Timestamp("2024-12-01")], "ttm_pe": [20.0]})


class FakeTreasure:
    def daily_treasure_yield(self):
        return pd.DataFrame(
            {
                "report_date": pd.date_range("2024-01-01", periods=30, freq="B"),
                "bc2_year": [0.04] * 30,
                "bc10_year": [0.045] * 30,
            }
        )


class FakeUtil:
    @staticmethod
    def load_sp500_historical_annual_returns():
        return pd.DataFrame({"report_date": [pd.Timestamp("2020-01-01")], "annual_returns": [0.1]})

    @staticmethod
    def sp500_cagr_returns(years: int):
        return pd.DataFrame({"report_date": [pd.Timestamp("2020-01-01")], "cagr": [0.08]})

    @staticmethod
    def sp500_cagr_returns_rolling(years: int):
        return pd.DataFrame({"start_date": [pd.Timestamp("2020-01-01")], "end_date": [pd.Timestamp("2024-01-01")], "cagr": [0.09]})


def _client(tmp_path: Path) -> DefeatBetaClient:
    cache = FileCache(tmp_path, default_ttl_seconds=60)
    client = DefeatBetaClient(cache, policy=CachePolicy(), price_fetch_overrides={"AGG": "TLT", "local": "local"})
    client._ticker_cls = FakeTicker
    client._treasure_cls = FakeTreasure
    client._util_module = FakeUtil()
    return client


def test_normalize_frame_none():
    assert DefeatBetaClient._normalize_frame(None).empty


def test_resolve_price_fetch_symbol_overrides(tmp_path: Path):
    c = _client(tmp_path)
    assert c._resolve_price_fetch_symbol("AGG") == "TLT"
    assert c._resolve_price_fetch_symbol("agg") == "TLT"
    assert c._resolve_price_fetch_symbol("SPY") == "SPY"


def test_latest_timestamp_empty_and_nonempty():
    assert DefeatBetaClient.latest_timestamp([]) is None
    assert DefeatBetaClient.latest_timestamp([pd.DataFrame()]) is None
    df = pd.DataFrame({"report_date": [pd.Timestamp("2024-01-05"), pd.Timestamp("2024-01-10")]})
    ts = DefeatBetaClient.latest_timestamp([df])
    assert ts is not None


def test_get_prices_and_return_series(tmp_path: Path):
    c = _client(tmp_path)
    r = c.get_prices("SPY")
    assert not r.data.empty
    rs = c.get_return_series("SPY", [1, 5])
    assert "return_1d" in rs.data.columns


def test_get_return_series_empty_price(tmp_path: Path):
    c = _client(tmp_path)

    class EmptyTicker(FakeTicker):
        def price(self):
            return pd.DataFrame()

    c._ticker_cls = EmptyTicker
    out = c.get_return_series("SPY", [1])
    assert out.data.empty


def test_get_price_ratio_branches(tmp_path: Path):
    c = _client(tmp_path)
    merged = c.get_price_ratio_history("SPY", "AGG")
    assert not merged.data.empty


def test_get_price_ratio_empty_side(tmp_path: Path):
    c = _client(tmp_path)

    class T1(FakeTicker):
        def price(self):
            return pd.DataFrame()

    c._ticker_cls = T1
    out = c.get_price_ratio_history("SPY", "AGG")
    assert out.data.empty


def test_get_yield_series_delegates(tmp_path: Path):
    c = _client(tmp_path)
    y = c.get_yield_series()
    assert not y.data.empty


def test_treasury_sp500_cagr_methods(tmp_path: Path):
    c = _client(tmp_path)
    assert not c.get_treasury_yields().data.empty
    assert not c.get_sp500_history().data.empty
    assert not c.get_sp500_cagr(5).data.empty
    assert not c.get_sp500_cagr_rolling(5).data.empty


def test_get_beta_calendar_info_news_filings_transcripts_revenue(tmp_path: Path):
    c = _client(tmp_path)
    for method in (c.get_beta,):
        assert not method("SPY", "SPY").data.empty
    assert not c.get_calendar("SPY").data.empty
    assert not c.get_info("SPY").data.empty
    assert not c.get_news("SPY").data.empty
    assert not c.get_filings("SPY").data.empty
    assert not c.get_transcripts("SPY").data.empty
    assert not c.get_revenue_by_segment("SPY").data.empty
    assert not c.get_revenue_by_geography("SPY").data.empty


def test_get_metric_frame_supported_and_missing(tmp_path: Path):
    c = _client(tmp_path)
    ok = c.get_metric_frame("SPY", "ttm_pe")
    assert not ok.data.empty
    bad = c.get_metric_frame("SPY", "not_a_real_method_xyz_999")
    assert bad.data.empty
    assert bad.errors


def test_safe_cached_frame_swallows_cache_error(tmp_path: Path):
    cache = _ExplodingCache(tmp_path, default_ttl_seconds=60)
    c = DefeatBetaClient(cache, policy=CachePolicy())
    c._ticker_cls = FakeTicker
    out = c.get_prices("SPY")
    assert out.data.empty
    assert "cache boom" in out.errors[0]


def test_lazy_import_populates_real_defeatbeta_modules(tmp_path: Path):
    cache = FileCache(tmp_path, default_ttl_seconds=60)
    c = DefeatBetaClient(cache)
    c._lazy_import()
    assert c._ticker_cls is not None
    assert c._treasure_cls is not None
    assert c._util_module is not None


def test_get_price_ratio_non_overlapping_dates(tmp_path: Path):
    c = _client(tmp_path)

    class A(FakeTicker):
        def price(self):
            return pd.DataFrame({"report_date": [pd.Timestamp("2024-01-01")], "close": [1.0]})

    class B(FakeTicker):
        def price(self):
            return pd.DataFrame({"report_date": [pd.Timestamp("2025-01-01")], "close": [1.0]})

    def ticker_factory(sym: str):
        return A(sym) if sym == "SPY" else B(sym)

    c._ticker_cls = ticker_factory  # type: ignore[assignment]
    out = c.get_price_ratio_history("SPY", "AGG")
    assert out.data.empty


def test_lazy_import_raises_when_defeatbeta_missing(monkeypatch, tmp_path: Path):
    real_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if isinstance(name, str) and name.startswith("defeatbeta_api"):
            raise ImportError("missing")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    cache = FileCache(tmp_path, default_ttl_seconds=60)
    c = DefeatBetaClient(cache)
    c._ticker_cls = None
    with pytest.raises(RuntimeError, match="defeatbeta-api is required"):
        c._lazy_import()
