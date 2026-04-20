from __future__ import annotations

from datetime import datetime
from typing import Literal

import numpy as np
import pandas as pd

from app.models import ChartSeries, PriceStats

RangeKey = Literal["1D", "7D", "30D", "90D", "1Y", "ALL"]

TRADING_DAYS_PER_YEAR = 252


def _latest_ts(df: pd.DataFrame) -> pd.Timestamp | None:
    if df.empty or "report_date" not in df.columns:
        return None
    return pd.Timestamp(df["report_date"].iloc[-1])


def _anchor_close(df: pd.DataFrame, latest: pd.Timestamp, calendar_days: int) -> float | None:
    target = latest - pd.Timedelta(days=calendar_days)
    sub = df[df["report_date"] <= target]
    if sub.empty:
        return None
    val = sub.iloc[-1]["close"]
    if pd.isna(val):
        return None
    return float(val)


def _first_close_of_year(df: pd.DataFrame, latest: pd.Timestamp) -> float | None:
    year_start = pd.Timestamp(year=latest.year, month=1, day=1)
    sub = df[df["report_date"] >= year_start]
    if sub.empty:
        return None
    val = sub.iloc[0]["close"]
    if pd.isna(val):
        return None
    return float(val)


def add_moving_averages(df: pd.DataFrame, windows: tuple[int, ...]) -> pd.DataFrame:
    out = df.copy()
    if "close" not in out.columns:
        return out
    for w in windows:
        out[f"ma{w}"] = out["close"].rolling(window=w, min_periods=w).mean()
    return out


def slice_chart_history(df: pd.DataFrame, range_key: RangeKey) -> pd.DataFrame:
    """Slice OHLCV (+ MA columns) for chart display."""
    if df.empty:
        return df
    latest = _latest_ts(df)
    if latest is None:
        return df.iloc[0:0]
    if range_key == "ALL":
        return df
    if range_key == "1D":
        return df.tail(1)
    days = {"7D": 7, "30D": 30, "90D": 90, "1Y": 365}.get(range_key, 90)
    start = latest - pd.Timedelta(days=days)
    sl = df[df["report_date"] > start]
    return sl if not sl.empty else df.tail(1)


def build_chart_series(df_slice: pd.DataFrame, ma_windows: tuple[int, ...]) -> ChartSeries:
    dates: list[datetime] = []
    close: list[float] = []
    ma20: list[float | None] = []
    ma50: list[float | None] = []
    vol: list[float] = []
    has20 = 20 in ma_windows
    has50 = 50 in ma_windows
    for _, row in df_slice.iterrows():
        rd = row["report_date"]
        ts = pd.Timestamp(rd)
        dates.append(datetime(ts.year, ts.month, ts.day))
        close.append(float(row["close"]))
        ma20.append(float(row["ma20"]) if has20 and "ma20" in row.index and pd.notna(row.get("ma20")) else None)
        ma50.append(float(row["ma50"]) if has50 and "ma50" in row.index and pd.notna(row.get("ma50")) else None)
        vv = row.get("volume")
        vol.append(float(vv) if vv is not None and pd.notna(vv) else 0.0)
    return ChartSeries(
        report_dates=dates,
        close=close,
        ma20=ma20,
        ma50=ma50,
        volume=vol,
    )


def _ma_state(last: float | None, ma: float | None) -> str | None:
    if last is None or ma is None or np.isnan(ma):
        return None
    return "above" if last >= ma else "below"


def _format_ma_chip(states: dict[str, str | None]) -> str:
    parts = []
    for label, st in states.items():
        if st:
            parts.append(f"{label} {st}")
    if not parts:
        return "Moving averages: —"
    return " · ".join(parts)


def compute_price_stats(df: pd.DataFrame, ma_windows: tuple[int, ...]) -> PriceStats:
    """Derive stats from full ascending history."""
    empty = PriceStats(
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
    )
    if df.empty or len(df) < 1:
        return empty
    if "close" not in df.columns:
        return empty

    latest = _latest_ts(df)
    if latest is None:
        return empty

    last_close = df.iloc[-1]["close"]
    if pd.isna(last_close):
        return empty
    last_close_f = float(last_close)

    if "high" in df.columns:
        ath = float(df["high"].max())
    else:
        ath = float(df["close"].max())
    dist_ath = (last_close_f / ath - 1.0) if ath else None

    ret_7d = ret_30d = ret_90d = ret_ytd = ret_1y = None
    a7 = _anchor_close(df, latest, 7)
    if a7 is not None and a7 > 0:
        ret_7d = last_close_f / a7 - 1.0
    a30 = _anchor_close(df, latest, 30)
    if a30 is not None and a30 > 0:
        ret_30d = last_close_f / a30 - 1.0
    a90 = _anchor_close(df, latest, 90)
    if a90 is not None and a90 > 0:
        ret_90d = last_close_f / a90 - 1.0
    y0 = _first_close_of_year(df, latest)
    if y0 is not None and y0 > 0:
        ret_ytd = last_close_f / y0 - 1.0
    a1y = _anchor_close(df, latest, 365)
    if a1y is not None and a1y > 0:
        ret_1y = last_close_f / a1y - 1.0

    vol_30d = None
    if len(df) >= 32:
        tail = df["close"].tail(31)
        rets = np.log(tail / tail.shift(1)).dropna()
        vol_30d = (
            float(rets.iloc[-30:].std() * np.sqrt(TRADING_DAYS_PER_YEAR)) if len(rets) >= 30 else None
        )

    ma20_s = ma50_s = ma200_s = None
    dfa = add_moving_averages(df, ma_windows)
    if "ma20" in dfa.columns and len(dfa):
        mv = dfa.iloc[-1]["ma20"]
        ma20_s = _ma_state(last_close_f, float(mv) if pd.notna(mv) else None)
    if "ma50" in dfa.columns and len(dfa):
        mv = dfa.iloc[-1]["ma50"]
        ma50_s = _ma_state(last_close_f, float(mv) if pd.notna(mv) else None)
    if "ma200" in dfa.columns and len(dfa):
        mv = dfa.iloc[-1]["ma200"]
        ma200_s = _ma_state(last_close_f, float(mv) if pd.notna(mv) else None)

    dd = None
    cmax = df["close"].cummax()
    peak = cmax.iloc[-1]
    if peak and peak > 0:
        dd = last_close_f / float(peak) - 1.0

    high_52w = low_52w = None
    win = df[df["report_date"] > latest - pd.Timedelta(days=365)]
    if not win.empty and "high" in win.columns and "low" in win.columns:
        high_52w = float(win["high"].max())
        low_52w = float(win["low"].min())

    avg_vol = latest_vol = None
    if "volume" in df.columns and len(df) >= 30:
        avg_vol = float(df["volume"].tail(30).mean())
    if "volume" in df.columns:
        vv = df.iloc[-1]["volume"]
        latest_vol = float(vv) if pd.notna(vv) else None

    return PriceStats(
        ret_7d=ret_7d,
        ret_30d=ret_30d,
        ret_90d=ret_90d,
        ret_ytd=ret_ytd,
        ret_1y=ret_1y,
        ath_price=ath,
        dist_from_ath_pct=dist_ath,
        vol_30d_ann=vol_30d,
        ma20_state=ma20_s,
        ma50_state=ma50_s,
        ma200_state=ma200_s,
        drawdown_from_peak_pct=dd,
        high_52w=high_52w,
        low_52w=low_52w,
        avg_volume_30d=avg_vol,
        latest_volume=latest_vol,
    )


def change_1d(df: pd.DataFrame) -> tuple[float | None, float | None]:
    if len(df) < 2:
        return None, None
    c0, c1 = df.iloc[-2]["close"], df.iloc[-1]["close"]
    if pd.isna(c0) or pd.isna(c1) or c0 == 0:
        return None, None
    c0f, c1f = float(c0), float(c1)
    return (c1f / c0f - 1.0), (c1f - c0f)


def ma_chip_text(df: pd.DataFrame, ma_windows: tuple[int, ...]) -> str:
    if df.empty:
        return "Moving averages: —"
    last = df.iloc[-1]["close"]
    if pd.isna(last):
        return "Moving averages: —"
    last_f = float(last)
    dfa = add_moving_averages(df, ma_windows)
    labels = {20: "20D", 50: "50D", 200: "200D"}
    states: dict[str, str | None] = {}
    for w in ma_windows:
        col = f"ma{w}"
        lab = labels.get(w, f"{w}D")
        mv = dfa.iloc[-1][col]
        st = _ma_state(last_f, float(mv) if pd.notna(mv) else None)
        states[lab] = "above" if st == "above" else "below" if st == "below" else None
    return _format_ma_chip(states)
