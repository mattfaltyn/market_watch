from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from app.metrics import (
    add_moving_averages,
    build_chart_series,
    change_1d,
    compute_price_stats,
    ma_chip_text,
    slice_chart_history,
)
from app.dashboard import normalize_range_key


def _frame(n: int = 400, start: str = "2020-01-01") -> pd.DataFrame:
    idx = pd.date_range(start, periods=n, freq="D")
    base = np.linspace(100.0, 200.0, n) + np.sin(np.linspace(0, 10, n)) * 2
    return pd.DataFrame(
        {
            "report_date": idx.normalize(),
            "open": base,
            "high": base * 1.01,
            "low": base * 0.99,
            "close": base,
            "volume": np.linspace(1e6, 2e6, n),
        }
    )


def test_slice_chart_all_and_1d():
    df = _frame(100)
    assert len(slice_chart_history(df, "ALL")) == 100
    assert len(slice_chart_history(df, "1D")) == 1


def test_slice_chart_trailing_windows():
    df = _frame(400)
    for key in ("7D", "30D", "90D", "1Y"):
        sl = slice_chart_history(df, key)  # type: ignore[arg-type]
        assert not sl.empty


def test_slice_empty():
    empty = pd.DataFrame(columns=["report_date", "close"])
    assert slice_chart_history(empty, "90D").empty  # type: ignore[arg-type]


def test_add_moving_averages():
    df = _frame(250)
    out = add_moving_averages(df, (20, 50))
    assert "ma20" in out.columns
    assert out["ma20"].iloc[-1] == out["close"].rolling(20).mean().iloc[-1]


def test_build_chart_series():
    df = add_moving_averages(_frame(60), (20, 50))
    ch = build_chart_series(df.tail(30), (20, 50))
    assert len(ch.close) == 30
    assert len(ch.ma20) == 30


def test_change_1d():
    df = _frame(3)
    p, a = change_1d(df)
    assert p is not None and a is not None


def test_change_1d_short():
    df = _frame(1)
    assert change_1d(df) == (None, None)


def test_compute_price_stats_full():
    df = _frame(400)
    st = compute_price_stats(df, (20, 50, 200))
    assert st.ret_7d is not None
    assert st.ath_price is not None
    assert st.dist_from_ath_pct is not None
    assert st.vol_30d_ann is not None


def test_compute_price_stats_short_history():
    df = _frame(100)
    st = compute_price_stats(df, (20, 50, 200))
    assert st.ma200_state is None


def test_ma_chip():
    df = _frame(250)
    text = ma_chip_text(df, (20, 50, 200))
    assert "20D" in text or "Moving averages" in text


def test_normalize_range_key():
    assert normalize_range_key("30D", "90D") == "30D"
    assert normalize_range_key("bogus", "90D") == "90D"
    assert normalize_range_key(None, "bogus") == "90D"


def test_compute_empty_frame():
    st = compute_price_stats(pd.DataFrame(), (20,))
    assert st.ret_7d is None


def test_compute_no_close_column():
    st = compute_price_stats(pd.DataFrame({"x": [1]}), (20,))
    assert st.ret_7d is None


def test_fmt_helpers_nan():
    from app.dashboard import fmt_pct, fmt_usd

    nan = float("nan")
    assert fmt_usd(nan) == "\u2014"
    assert fmt_pct(nan) == "\u2014"


def test_slice_fallback_single_row():
    df = _frame(5)
    tiny = df.tail(1)
    sl = slice_chart_history(tiny, "7D")  # type: ignore[arg-type]
    assert len(sl) >= 1
