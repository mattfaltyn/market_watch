from __future__ import annotations

import builtins
from datetime import datetime
from pathlib import Path
from unittest import mock

import numpy as np
import pandas as pd
import pytest

from app.dashboard import build_page_content, build_price_figure, fmt_vol
from app.data.bitcoin_client import BitcoinDataClient, history_to_records
from app.data.cache import FileCache
from app.metrics import (
    _anchor_close,
    _first_close_of_year,
    add_moving_averages,
    build_chart_series,
    change_1d,
    compute_price_stats,
    ma_chip_text,
    slice_chart_history,
)
from app.models import BitcoinSnapshot, ChartSeries, PriceStats


def test_fmt_vol_billions():
    assert "B" in fmt_vol(3e9)


def test_yfinance_import_error(monkeypatch: pytest.MonkeyPatch):
    import sys

    sys.modules.pop("yfinance", None)
    real_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0, **kw):
        if name == "yfinance":
            raise ImportError("blocked")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    from app.data.bitcoin_client import _import_yfinance

    assert _import_yfinance() is None


def test_get_price_history_single_row(tmp_path: Path):
    idx = pd.date_range("2024-01-01", periods=1, freq="D", tz="UTC")
    raw = pd.DataFrame(
        {"Open": [1], "High": [2], "Low": [0], "Close": [1.5], "Volume": [10]},
        index=idx,
    )

    class _T:
        def history(self, period, auto_adjust):
            return raw

    class _YF:
        def Ticker(self, symbol):
            return _T()

    cache = FileCache(tmp_path / "cg", default_ttl_seconds=3600)
    client = BitcoinDataClient(cache, "BTC-USD", 900, (20, 50, 200))
    with mock.patch("app.data.bitcoin_client._import_yfinance", return_value=_YF()):
        res = client.get_price_history(force_refresh=True)
        assert "Insufficient" in res.errors[0]


def test_history_to_records_empty():
    assert history_to_records(pd.DataFrame()) == []


def test_cache_ttl_miss(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    import app.data.cache as cache_mod

    clock = {"t": 0.0}

    def fake_time() -> float:
        return clock["t"]

    monkeypatch.setattr(cache_mod.time, "time", fake_time)
    cache = FileCache(tmp_path / "ttl", default_ttl_seconds=1)
    clock["t"] = 0.0
    cache.set("k", 99)
    clock["t"] = 50_000.0
    assert cache.get("k", ttl_seconds=1) is None


def test_slice_chart_sl_empty_fallback():
    df = pd.DataFrame(
        {
            "report_date": pd.to_datetime(["2024-06-01"]),
            "close": [10.0],
            "high": [11.0],
            "low": [9.0],
        }
    )
    out = slice_chart_history(df, "7D")  # type: ignore[arg-type]
    assert len(out) == 1


def test_latest_ts_no_column():
    df = pd.DataFrame({"x": [1]})
    assert slice_chart_history(df, "ALL").empty  # type: ignore[arg-type]


def test_add_ma_no_close():
    df = pd.DataFrame({"report_date": [pd.Timestamp("2024-01-01")]})
    assert "ma20" not in add_moving_averages(df, (20,))


def test_ma_chip_partial_none():
    df = pd.DataFrame(
        {
            "report_date": pd.date_range("2024-01-01", periods=30, freq="D"),
            "close": range(30),
        }
    )
    text = ma_chip_text(df, (20,))
    assert isinstance(text, str)


def test_compute_price_stats_nan_close_last():
    df = pd.DataFrame(
        {
            "report_date": pd.date_range("2024-01-01", periods=5, freq="D"),
            "open": [1, 2, 3, 4, 5],
            "high": [2, 3, 4, 5, 6],
            "low": [0, 1, 2, 3, 4],
            "close": [1.5, 2.5, 3.5, 4.5, float("nan")],
            "volume": [1] * 5,
        }
    )
    st = compute_price_stats(df, (20,))
    assert st.ret_7d is None


def test_build_price_figure_with_mas(tmp_path: Path):
    idx = pd.date_range("2023-01-01", periods=120, freq="D", tz="UTC")
    raw = pd.DataFrame(
        {
            "Open": range(120),
            "High": [x + 1 for x in range(120)],
            "Low": range(120),
            "Close": [float(x) + 0.5 for x in range(120)],
            "Volume": [1e6] * 120,
        },
        index=idx,
    )

    class _T:
        def history(self, period, auto_adjust):
            return raw

    class _YF:
        def Ticker(self, symbol):
            return _T()

    cache = FileCache(tmp_path / "fig", default_ttl_seconds=3600)
    client = BitcoinDataClient(cache, "BTC-USD", 900, (20, 50, 200))
    with mock.patch("app.data.bitcoin_client._import_yfinance", return_value=_YF()):
        res = client.get_price_history()
        snap = client.build_snapshot(res.data, "90D")
        fig = build_price_figure(snap)
        assert fig.data


def test_build_page_hero_lines_and_range_note(tmp_path: Path):
    idx = pd.date_range("2023-01-01", periods=400, freq="D", tz="UTC")
    close = [100.0] * 398 + [100.0, 100.0]
    raw = pd.DataFrame(
        {
            "Open": close,
            "High": [c * 1.01 for c in close],
            "Low": [c * 0.99 for c in close],
            "Close": close,
            "Volume": [1e6] * 400,
        },
        index=idx,
    )

    class _T:
        def history(self, period, auto_adjust):
            return raw

    class _YF:
        def Ticker(self, symbol):
            return _T()

    cache = FileCache(tmp_path / "hero", default_ttl_seconds=3600)
    client = BitcoinDataClient(cache, "BTC-USD", 900, (20, 50, 200))
    with mock.patch("app.data.bitcoin_client._import_yfinance", return_value=_YF()):
        res = client.get_price_history()
        snap = client.build_snapshot(res.data, "1D")
        body = build_page_content(snap)
        assert body is not None
        snap2 = client.build_snapshot(res.data, "90D")
        assert build_page_content(snap2) is not None


def test_volume_sparkline_empty_volume():
    snap = BitcoinSnapshot(
        symbol="BTC-USD",
        as_of=None,
        latest_price=1.0,
        change_1d_pct=None,
        change_1d_abs=None,
        ma_summary_chip="x",
        stats=PriceStats(
            ret_7d=None,
            ret_30d=None,
            ret_90d=None,
            ret_ytd=None,
            ret_1y=None,
            ath_price=None,
            dist_from_ath_pct=None,
            vol_30d_ann=None,
            ma20_state=None,
            ma50_state=None,
            ma200_state=None,
            drawdown_from_peak_pct=None,
            high_52w=None,
            low_52w=None,
            avg_volume_30d=None,
            latest_volume=None,
        ),
        chart=ChartSeries(report_dates=[__import__("datetime").datetime(2024, 1, 1)], close=[1.0], ma20=[1.0], ma50=[1.0], volume=[]),
        range_key="90D",
    )
    assert build_page_content(snap) is not None


def test_build_chart_series_without_ma50_window():
    df = add_moving_averages(
        pd.DataFrame(
            {
                "report_date": pd.date_range("2024-01-01", periods=40, freq="D"),
                "close": range(40),
            }
        ),
        (20,),
    )
    ch = build_chart_series(df, (20,))
    assert len(ch.close) == 40


def test_compute_ath_close_column_only():
    df = pd.DataFrame(
        {
            "report_date": pd.date_range("2024-01-01", periods=60, freq="D"),
            "close": range(60),
            "volume": [1] * 60,
        }
    )
    st = compute_price_stats(df, (20, 50))
    assert st.ath_price is not None


def test_compute_latest_none():
    df = pd.DataFrame({"close": [1.0, 2.0]})
    st = compute_price_stats(df, (20,))
    assert st.ret_7d is None


def test_vol_branch_short_returns():
    df = pd.DataFrame(
        {
            "report_date": pd.date_range("2024-01-01", periods=20, freq="D"),
            "close": range(20),
            "high": range(20),
            "low": range(20),
            "volume": [1] * 20,
        }
    )
    st = compute_price_stats(df, (20,))
    assert st.vol_30d_ann is None


def test_change_1d_zero_denominator():
    df = pd.DataFrame({"close": [0.0, 1.0]})
    assert change_1d(df) == (None, None)


def test_ma_chip_missing_column_branch():
    df = pd.DataFrame(
        {
            "report_date": pd.date_range("2024-01-01", periods=50, freq="D"),
            "close": range(50),
        }
    )
    assert isinstance(ma_chip_text(df, (99,)), str)


def test_price_figure_ma50_only_trace(tmp_path: Path):
    idx = pd.date_range("2023-01-01", periods=120, freq="D", tz="UTC")
    raw = pd.DataFrame(
        {
            "Open": range(120),
            "High": [x + 1 for x in range(120)],
            "Low": range(120),
            "Close": [float(x) + 0.5 for x in range(120)],
            "Volume": [1e6] * 120,
        },
        index=idx,
    )

    class _T:
        def history(self, period, auto_adjust):
            return raw

    class _YF:
        def Ticker(self, symbol):
            return _T()

    cache = FileCache(tmp_path / "ma50", default_ttl_seconds=3600)
    client = BitcoinDataClient(cache, "BTC-USD", 900, (50, 200))
    with mock.patch("app.data.bitcoin_client._import_yfinance", return_value=_YF()):
        res = client.get_price_history()
        snap = client.build_snapshot(res.data, "90D")
        fig = build_price_figure(snap)
        assert len(fig.data) >= 1


def test_import_yfinance_returns_module():
    from app.data import bitcoin_client as bc

    assert bc._import_yfinance() is not None


def test_anchor_close_nan_value():
    df = pd.DataFrame(
        {
            "report_date": [pd.Timestamp("2024-01-01"), pd.Timestamp("2024-01-09")],
            "close": [float("nan"), 2.0],
        }
    )
    assert _anchor_close(df, pd.Timestamp("2024-01-09"), 7) is None


def test_first_close_of_year_empty_window():
    df = pd.DataFrame({"report_date": [pd.Timestamp("2023-06-01")], "close": [1.0]})
    assert _first_close_of_year(df, pd.Timestamp("2024-06-15")) is None


def test_vol_short_returns_path():
    n = 40
    close = np.concatenate([np.full(8, np.nan), np.linspace(1.0, 2.0, n - 8)])
    df = pd.DataFrame(
        {
            "report_date": pd.date_range("2020-01-01", periods=n, freq="D"),
            "close": close,
            "high": close,
            "low": close,
            "volume": np.ones(n),
        }
    )
    st = compute_price_stats(df, (20,))
    assert st.vol_30d_ann is None or isinstance(st.vol_30d_ann, float)


def test_drawdown_no_peak():
    df = pd.DataFrame(
        {
            "report_date": pd.date_range("2024-01-01", periods=3, freq="D"),
            "close": [0.0, 0.0, 0.0],
            "high": [0.0, 0.0, 0.0],
            "low": [0.0, 0.0, 0.0],
            "volume": [1, 1, 1],
        }
    )
    st = compute_price_stats(df, (20,))
    assert st.drawdown_from_peak_pct is None


def test_latest_volume_nan():
    vols = [1.0] * 39 + [float("nan")]
    df = pd.DataFrame(
        {
            "report_date": pd.date_range("2024-01-01", periods=40, freq="D"),
            "close": range(40),
            "high": range(40),
            "low": range(40),
            "volume": vols,
        }
    )
    st = compute_price_stats(df, (20,))
    assert st.latest_volume is None


def test_ma_chip_empty_frame():
    assert ma_chip_text(pd.DataFrame(), (20,)) == "Moving averages: —"


def test_ma_chip_nan_last():
    df = pd.DataFrame(
        {
            "report_date": pd.date_range("2024-01-01", periods=5, freq="D"),
            "close": list(range(4)) + [float("nan")],
        }
    )
    assert ma_chip_text(df, (20,)) == "Moving averages: —"


def test_no_volume_column_latest():
    df = pd.DataFrame(
        {
            "report_date": pd.date_range("2020-01-01", periods=50, freq="D"),
            "close": range(50),
            "high": range(50),
            "low": range(50),
        }
    )
    st = compute_price_stats(df, (20,))
    assert st.latest_volume is None


def test_fifty_two_week_without_high_column():
    df = pd.DataFrame(
        {
            "report_date": pd.date_range("2020-01-01", periods=400, freq="D"),
            "close": range(400),
            "low": range(400),
            "volume": [1] * 400,
        }
    )
    st = compute_price_stats(df, (20,))
    assert st.high_52w is None


def test_avg_volume_short_history():
    df = pd.DataFrame(
        {
            "report_date": pd.date_range("2024-01-01", periods=10, freq="D"),
            "close": range(10),
            "high": range(10),
            "low": range(10),
            "volume": [1.0] * 10,
        }
    )
    st = compute_price_stats(df, (20,))
    assert st.avg_volume_30d is None
    assert st.latest_volume == 1.0


def test_build_price_figure_only_price_trace():
    d = datetime(2024, 1, 1)
    snap = BitcoinSnapshot(
        symbol="BTC-USD",
        as_of=d,
        latest_price=2.0,
        change_1d_pct=None,
        change_1d_abs=None,
        ma_summary_chip="x",
        stats=PriceStats(
            ret_7d=None,
            ret_30d=None,
            ret_90d=None,
            ret_ytd=None,
            ret_1y=None,
            ath_price=None,
            dist_from_ath_pct=None,
            vol_30d_ann=None,
            ma20_state=None,
            ma50_state=None,
            ma200_state=None,
            drawdown_from_peak_pct=None,
            high_52w=None,
            low_52w=None,
            avg_volume_30d=None,
            latest_volume=None,
        ),
        chart=ChartSeries(
            report_dates=[d, datetime(2024, 1, 2)],
            close=[1.0, 2.0],
            ma20=[None, None],
            ma50=[None, None],
            volume=[1.0, 2.0],
        ),
        range_key="7D",
    )
    fig = build_price_figure(snap)
    assert len(fig.data) == 1


def test_build_price_figure_ma20_without_ma50():
    d = datetime(2024, 1, 1)
    snap = BitcoinSnapshot(
        symbol="BTC-USD",
        as_of=d,
        latest_price=2.0,
        change_1d_pct=None,
        change_1d_abs=None,
        ma_summary_chip="x",
        stats=PriceStats(
            ret_7d=None,
            ret_30d=None,
            ret_90d=None,
            ret_ytd=None,
            ret_1y=None,
            ath_price=None,
            dist_from_ath_pct=None,
            vol_30d_ann=None,
            ma20_state=None,
            ma50_state=None,
            ma200_state=None,
            drawdown_from_peak_pct=None,
            high_52w=None,
            low_52w=None,
            avg_volume_30d=None,
            latest_volume=None,
        ),
        chart=ChartSeries(
            report_dates=[d, datetime(2024, 1, 2)],
            close=[1.0, 2.0],
            ma20=[1.2, 1.4],
            ma50=[None, None],
            volume=[1.0, 2.0],
        ),
        range_key="7D",
    )
    fig = build_price_figure(snap)
    assert len(fig.data) == 2
