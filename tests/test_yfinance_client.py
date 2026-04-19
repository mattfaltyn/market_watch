from __future__ import annotations

import builtins
import sys

import pandas as pd

from app.data.yfinance_client import YFinanceFetcher, fetch_prices_yfinance


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
