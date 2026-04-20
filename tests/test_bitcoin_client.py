from __future__ import annotations

from pathlib import Path
from unittest import mock

import pandas as pd

from app.data.bitcoin_client import BitcoinDataClient, fetch_btc_history_yfinance, history_to_records, records_to_history
from app.data.cache import FileCache


def _hist_df():
    idx = pd.date_range("2024-01-01", periods=5, freq="D", tz="UTC")
    return pd.DataFrame(
        {"Open": [1, 2, 3, 4, 5], "High": [2, 3, 4, 5, 6], "Low": [0.5, 1, 2, 3, 4], "Close": [1.5, 2.5, 3.5, 4.5, 5.5], "Volume": [100] * 5},
        index=idx,
    )


def test_fetch_btc_no_yfinance():
    with mock.patch("app.data.bitcoin_client._import_yfinance", return_value=None):
        assert fetch_btc_history_yfinance("BTC-USD").empty


def test_fetch_btc_ok():
    class _T:
        def history(self, period, auto_adjust):
            return _hist_df()

    class _YF:
        def Ticker(self, symbol):
            return _T()

    with mock.patch("app.data.bitcoin_client._import_yfinance", return_value=_YF()):
        df = fetch_btc_history_yfinance("BTC-USD")
        assert len(df) == 5
        assert "close" in df.columns


def test_fetch_btc_ticker_raises():
    class _T:
        def history(self, period, auto_adjust):
            raise RuntimeError("network")

    class _YF:
        def Ticker(self, symbol):
            return _T()

    with mock.patch("app.data.bitcoin_client._import_yfinance", return_value=_YF()):
        assert fetch_btc_history_yfinance("BTC-USD").empty


def test_client_cache_and_force(tmp_path: Path):
    class _T:
        def history(self, period, auto_adjust):
            return _hist_df()

    class _YF:
        def Ticker(self, symbol):
            return _T()

    cache = FileCache(tmp_path / "bc", default_ttl_seconds=3600)
    client = BitcoinDataClient(cache, "BTC-USD", 900, (20, 50, 200))
    with mock.patch("app.data.bitcoin_client._import_yfinance", return_value=_YF()):
        r1 = client.get_price_history(force_refresh=False)
        r2 = client.get_price_history(force_refresh=False)
        r3 = client.get_price_history(force_refresh=True)
        assert not r1.data.empty
        assert len(r2.data) == len(r3.data)


def test_records_roundtrip():
    df = pd.DataFrame(
        {
            "report_date": pd.to_datetime(["2024-01-01", "2024-01-02"]),
            "open": [1.0, 2.0],
            "high": [2.0, 3.0],
            "low": [0.5, 1.0],
            "close": [1.5, 2.5],
            "volume": [10.0, 20.0],
        }
    )
    rec = history_to_records(df)
    back = records_to_history(rec)
    assert len(back) == 2


def test_build_snapshot(tmp_path: Path):
    class _T:
        def history(self, period, auto_adjust):
            return _hist_df()

    class _YF:
        def Ticker(self, symbol):
            return _T()

    cache = FileCache(tmp_path / "bc3", default_ttl_seconds=3600)
    client = BitcoinDataClient(cache, "BTC-USD", 900, (20, 50, 200))
    with mock.patch("app.data.bitcoin_client._import_yfinance", return_value=_YF()):
        res = client.get_price_history()
        snap = client.build_snapshot(res.data, "90D")
        assert snap.latest_price is not None


def test_get_price_history_cache_error(tmp_path: Path):
    cache = FileCache(tmp_path / "bc4", default_ttl_seconds=3600)
    client = BitcoinDataClient(cache, "BTC-USD", 900, (20, 50, 200))
    with mock.patch.object(cache, "get_or_set", side_effect=OSError("disk")):
        res = client.get_price_history(force_refresh=True)
        assert res.data.empty
        assert "Cache error" in res.errors[0]


def test_get_price_history_invalid_cache_payload(tmp_path: Path):
    cache = FileCache(tmp_path / "bc5", default_ttl_seconds=3600)
    client = BitcoinDataClient(cache, "BTC-USD", 900, (20, 50, 200))
    with mock.patch.object(cache, "get_or_set", return_value="not-a-frame"):
        res = client.get_price_history(force_refresh=True)
        assert res.data.empty
        assert "Invalid cached payload" in res.errors[0]
