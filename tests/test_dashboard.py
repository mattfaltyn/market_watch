from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from unittest import mock

import pandas as pd
from app.config import load_config
from app.dashboard import (
    build_empty_state,
    build_error_banner,
    build_page_content,
    build_price_figure,
    coalesce_history,
    create_app_layout,
    refresh_state_payload,
    run_dashboard_fetch,
    should_force_refresh,
)
from app.data.bitcoin_client import BitcoinDataClient
from app.data.cache import FileCache
from app.models import BitcoinSnapshot, ChartSeries, DataResult, PriceStats


def _big_frame():
    idx = pd.date_range("2020-01-01", periods=400, freq="D")
    base = range(400)
    return pd.DataFrame(
        {
            "report_date": idx.normalize(),
            "open": base,
            "high": [x + 1 for x in base],
            "low": [x - 1 for x in base],
            "close": [float(x) + 0.5 for x in base],
            "volume": [1e6] * 400,
        }
    )


def test_coalesce_prior_on_failure():
    from app.data.bitcoin_client import history_to_records

    prior = _big_frame().head(5)
    rec = history_to_records(prior)
    empty = DataResult(data=pd.DataFrame(), errors=["upstream failed"])
    df, errs = coalesce_history(rec, empty)
    assert len(df) == 5
    assert "upstream failed" in errs[0]


def test_build_error_banner():
    assert build_error_banner([]) is not None
    assert build_error_banner(["e"]) is not None


def test_build_price_figure_empty_snapshot():
    snap = BitcoinSnapshot(
        symbol="BTC-USD",
        as_of=None,
        latest_price=None,
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
        chart=ChartSeries(report_dates=[], close=[], ma20=[], ma50=[], volume=[]),
        range_key="90D",
    )
    fig = build_price_figure(snap)
    assert fig is not None


def test_create_app_layout_bad_default_range():
    cfg = load_config()
    cfg2 = replace(cfg, dashboard=replace(cfg.dashboard, default_range="invalid"))
    layout = create_app_layout(cfg2)
    assert layout is not None


def test_refresh_helpers():
    assert should_force_refresh("refresh-state", {"refresh": 1}) is True
    assert should_force_refresh("url", {"refresh": 1}) is False
    assert refresh_state_payload(2, {"refresh": 1})["refresh"] == 2


def test_run_dashboard_fetch(tmp_path: Path):
    class _T:
        def history(self, period, auto_adjust):
            idx = pd.date_range("2024-01-01", periods=120, freq="D", tz="UTC")
            return pd.DataFrame(
                {"Open": range(120), "High": range(120), "Low": range(120), "Close": range(120), "Volume": [100] * 120},
                index=idx,
            )

    class _YF:
        def Ticker(self, symbol):
            return _T()

    cache = FileCache(tmp_path / "db", default_ttl_seconds=3600)
    client = BitcoinDataClient(cache, "BTC-USD", 900, (20, 50, 200))
    cfg = load_config()
    with mock.patch("app.data.bitcoin_client._import_yfinance", return_value=_YF()):
        banner, header, store, body = run_dashboard_fetch("url", "90D", {"refresh": 0}, None, client, cfg)
        assert store["records"]
        assert body is not None
        banner2, _, _, _ = run_dashboard_fetch("refresh-state", "90D", {"refresh": 1}, {"records": store["records"]}, client, cfg)
        assert banner2 is not None


def test_build_page_content_smoke(tmp_path: Path):
    idx = pd.date_range("2020-01-01", periods=250, freq="D", tz="UTC")
    raw = pd.DataFrame(
        {
            "Open": range(250),
            "High": [x + 1 for x in range(250)],
            "Low": [max(0, x - 1) for x in range(250)],
            "Close": [float(x) + 0.5 for x in range(250)],
            "Volume": [1e6] * 250,
        },
        index=idx,
    )

    class _T:
        def history(self, period, auto_adjust):
            return raw

    class _YF:
        def Ticker(self, symbol):
            return _T()

    cache = FileCache(tmp_path / "db2", default_ttl_seconds=3600)
    client = BitcoinDataClient(cache, "BTC-USD", 900, (20, 50, 200))
    with mock.patch("app.data.bitcoin_client._import_yfinance", return_value=_YF()):
        res = client.get_price_history()
        snap = client.build_snapshot(res.data, "1D")
        body = build_page_content(snap)
        assert body is not None


def test_render_empty_state():
    assert build_empty_state() is not None


def test_fmt_vol_units():
    from app.dashboard import fmt_vol

    assert "B" in fmt_vol(2e9)
    assert "M" in fmt_vol(2e6)
    assert "K" in fmt_vol(2e3)
    assert fmt_vol(42.0) == "42"


def test_run_dashboard_fetch_empty_upstream(tmp_path: Path):
    class _T:
        def history(self, period, auto_adjust):
            return pd.DataFrame()

    class _YF:
        def Ticker(self, symbol):
            return _T()

    cache = FileCache(tmp_path / "db3", default_ttl_seconds=3600)
    client = BitcoinDataClient(cache, "BTC-USD", 900, (20, 50, 200))
    cfg = load_config()
    with mock.patch("app.data.bitcoin_client._import_yfinance", return_value=_YF()):
        _, _, store, body = run_dashboard_fetch("url", "90D", {"refresh": 0}, None, client, cfg)
        assert store["records"] == []
        assert body is not None
