from __future__ import annotations

from typing import Any

import pandas as pd

from app.data.cache import FileCache
from app.metrics import (
    RangeKey,
    add_moving_averages,
    build_chart_series,
    change_1d,
    compute_price_stats,
    ma_chip_text,
    slice_chart_history,
)
from app.models import BitcoinSnapshot, ChartSeries, DataResult, PriceStats


def _import_yfinance():
    try:
        import yfinance as yf  # noqa: PLC0415
    except ImportError:
        return None
    return yf


def _history_to_df(hist: pd.DataFrame | None) -> pd.DataFrame:
    if hist is None or hist.empty:
        return pd.DataFrame()
    out = pd.DataFrame(
        {
            "report_date": pd.to_datetime(hist.index, utc=True).tz_convert(None).normalize(),
            "open": pd.to_numeric(hist.get("Open"), errors="coerce"),
            "high": pd.to_numeric(hist.get("High"), errors="coerce"),
            "low": pd.to_numeric(hist.get("Low"), errors="coerce"),
            "close": pd.to_numeric(hist.get("Close"), errors="coerce"),
            "volume": pd.to_numeric(hist.get("Volume"), errors="coerce"),
        }
    )
    out = out.dropna(subset=["report_date", "close"])
    return out.sort_values("report_date").reset_index(drop=True)


def fetch_btc_history_yfinance(symbol: str) -> pd.DataFrame:
    yf = _import_yfinance()
    if yf is None:
        return pd.DataFrame()
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="max", auto_adjust=False)
    except Exception:
        return pd.DataFrame()
    return _history_to_df(hist)


_CACHE_KEY = "btc-usd-daily-history"


def _safe_key_fragment(symbol: str) -> str:
    return "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in symbol)


class BitcoinDataClient:
    """Yahoo Finance BTC-USD daily history with file caching."""

    def __init__(
        self,
        cache: FileCache,
        symbol: str,
        market_ttl_seconds: int,
        moving_averages: tuple[int, ...],
    ) -> None:
        self.cache = cache
        self.symbol = symbol
        self.market_ttl_seconds = market_ttl_seconds
        self.moving_averages = moving_averages
        self._cache_key = f"{_CACHE_KEY}-{_safe_key_fragment(symbol)}"

    def get_price_history(self, force_refresh: bool = False) -> DataResult:
        errors: list[str] = []

        def load() -> pd.DataFrame:
            return fetch_btc_history_yfinance(self.symbol)

        try:
            frame = self.cache.get_or_set(
                self._cache_key,
                load,
                ttl_seconds=self.market_ttl_seconds,
                force_refresh=force_refresh,
            )
        except OSError as exc:
            return DataResult(data=pd.DataFrame(), errors=[f"Cache error: {exc}"])
        if not isinstance(frame, pd.DataFrame):
            return DataResult(data=pd.DataFrame(), errors=["Invalid cached payload"])
        if frame.empty:
            errors.append("No price history returned from Yahoo Finance.")
            return DataResult(data=frame, errors=errors)
        if len(frame) < 2:
            errors.append("Insufficient BTC history for metrics.")
            return DataResult(data=frame, errors=errors)
        return DataResult(data=frame, errors=errors)

    def build_snapshot(
        self,
        history: pd.DataFrame,
        range_key: RangeKey,
    ) -> BitcoinSnapshot:
        ma_w = self.moving_averages
        if history.empty or len(history) < 1:
            return _empty_snapshot(self.symbol, range_key)

        full = add_moving_averages(history, ma_w)
        chart_df = slice_chart_history(full, range_key)
        chart = build_chart_series(chart_df, ma_w)
        stats = compute_price_stats(history, ma_w)
        pchg, pch_abs = change_1d(history)
        chip = ma_chip_text(history, ma_w)
        latest = history.iloc[-1]["close"]
        latest_f = float(latest) if pd.notna(latest) else None
        as_of = history.iloc[-1]["report_date"]
        as_of_dt = pd.Timestamp(as_of).to_pydatetime() if pd.notna(as_of) else None

        return BitcoinSnapshot(
            symbol=self.symbol,
            as_of=as_of_dt,
            latest_price=latest_f,
            change_1d_pct=pchg,
            change_1d_abs=pch_abs,
            ma_summary_chip=chip,
            stats=stats,
            chart=chart,
            range_key=range_key,
        )


def _empty_snapshot(symbol: str, range_key: RangeKey) -> BitcoinSnapshot:
    empty_stats = PriceStats(
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
    return BitcoinSnapshot(
        symbol=symbol,
        as_of=None,
        latest_price=None,
        change_1d_pct=None,
        change_1d_abs=None,
        ma_summary_chip="Moving averages: —",
        stats=empty_stats,
        chart=ChartSeries(report_dates=[], close=[], ma20=[], ma50=[], volume=[]),
        range_key=range_key,
    )


def history_to_records(df: pd.DataFrame) -> list[dict[str, Any]]:
    if df.empty:
        return []
    out = df.copy()
    out["report_date"] = out["report_date"].astype(str)
    return out.to_dict("records")


def records_to_history(records: list[dict[str, Any]] | None) -> pd.DataFrame:
    if not records:
        return pd.DataFrame()
    df = pd.DataFrame(records)
    df["report_date"] = pd.to_datetime(df["report_date"])
    for col in ("open", "high", "low", "close", "volume", "ma20", "ma50", "ma200"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df.sort_values("report_date").reset_index(drop=True)
