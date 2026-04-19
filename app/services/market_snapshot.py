from __future__ import annotations

from dataclasses import asdict

import pandas as pd

from app.models import MarketIndexSnapshot, MarketSnapshot, RatesSnapshot


BENCHMARKS = ("SPY", "QQQ", "IWM", "DIA")


def _latest_return(series: pd.Series, periods: int) -> float | None:
    if len(series) <= periods:
        return None
    return float(series.iloc[-1] / series.iloc[-(periods + 1)] - 1.0)


def _ma_state(close: pd.Series, window: int) -> str:
    if close.empty or len(close) < window:
        return "unavailable"
    moving_average = close.rolling(window=window).mean().iloc[-1]
    return "above" if close.iloc[-1] >= moving_average else "below"


def build_market_snapshot(client, symbols: list[str] | None = None, force_refresh: bool = False) -> MarketSnapshot:
    symbols = symbols or list(BENCHMARKS)
    snapshots: list[MarketIndexSnapshot] = []

    for symbol in symbols:
        result = client.get_prices(symbol, force_refresh=force_refresh)
        src = client.last_price_source(symbol) if hasattr(client, "last_price_source") else None
        frame = result.data.sort_values("report_date") if not result.data.empty else pd.DataFrame()
        if frame.empty or "close" not in frame.columns:
            snapshots.append(
                MarketIndexSnapshot(
                    symbol=symbol,
                    close=None,
                    return_1d=None,
                    return_5d=None,
                    return_1m=None,
                    realized_vol_20d=None,
                    ma20_state="unavailable",
                    ma50_state="unavailable",
                    ma200_state="unavailable",
                    as_of=None,
                    source=src,
                )
            )
            continue

        close = pd.to_numeric(frame["close"], errors="coerce").dropna()
        returns = close.pct_change()
        snapshots.append(
            MarketIndexSnapshot(
                symbol=symbol,
                close=float(close.iloc[-1]),
                return_1d=_latest_return(close, 1),
                return_5d=_latest_return(close, 5),
                return_1m=_latest_return(close, 21),
                realized_vol_20d=float(returns.tail(20).std() * (252 ** 0.5)) if len(returns.dropna()) >= 20 else None,
                ma20_state=_ma_state(close, 20),
                ma50_state=_ma_state(close, 50),
                ma200_state=_ma_state(close, 200),
                as_of=frame["report_date"].max().to_pydatetime() if "report_date" in frame.columns else None,
                source=src,
            )
        )

    positive_names = [item for item in snapshots if item.return_1m is not None and item.return_1m > 0]
    ratio = len(positive_names) / len(snapshots) if snapshots else 0.0
    as_of = max((item.as_of for item in snapshots if item.as_of is not None), default=None)
    return MarketSnapshot(indices=snapshots, positive_participation_ratio=ratio, as_of=as_of)


def build_rates_snapshot(client, force_refresh: bool = False) -> RatesSnapshot:
    result = client.get_treasury_yields(force_refresh=force_refresh)
    frame = result.data.sort_values("report_date") if not result.data.empty else pd.DataFrame()
    if frame.empty:
        return RatesSnapshot(None, None, None, None, None, None, None)  # type: ignore[arg-type]

    latest = frame.iloc[-1]
    y10_series = pd.to_numeric(frame.get("bc10_year"), errors="coerce")
    return RatesSnapshot(
        as_of=latest["report_date"].to_pydatetime(),
        y2=float(latest["bc2_year"]) if pd.notna(latest.get("bc2_year")) else None,
        y10=float(latest["bc10_year"]) if pd.notna(latest.get("bc10_year")) else None,
        y30=float(latest["bc30_year"]) if pd.notna(latest.get("bc30_year")) else None,
        spread_10y_short_proxy=float(latest["bc10_year"] - latest["bc2_year"])
        if pd.notna(latest.get("bc10_year")) and pd.notna(latest.get("bc2_year"))
        else None,
        change_10y_5d=float(y10_series.iloc[-1] - y10_series.iloc[-6]) if len(y10_series.dropna()) > 5 else None,
        change_10y_1m=float(y10_series.iloc[-1] - y10_series.iloc[-22]) if len(y10_series.dropna()) > 21 else None,
    )
