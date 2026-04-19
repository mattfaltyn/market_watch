from __future__ import annotations

import pandas as pd

from app.models import VamsSignal


def _safe_return(close: pd.Series, periods: int) -> float:
    if len(close) <= periods:
        return 0.0
    return float(close.iloc[-1] / close.iloc[-(periods + 1)] - 1.0)


def _latest_close(frame: pd.DataFrame) -> tuple[pd.Series, pd.Timestamp | None]:
    if frame.empty or "close" not in frame.columns:
        return pd.Series(dtype=float), None
    ordered = frame.sort_values("report_date")
    close = pd.to_numeric(ordered["close"], errors="coerce").dropna()
    return close, ordered["report_date"].max() if "report_date" in ordered.columns else None


def get_vams_signal(client, symbol: str, thresholds: dict[str, float], force_refresh: bool = False) -> VamsSignal:
    result = client.get_prices(symbol, force_refresh=force_refresh)
    close, as_of = _latest_close(result.data)
    if close.empty:
        return VamsSignal(symbol=symbol, state="neutral", score=0.0, volatility=None, trend=None, momentum=None, as_of=None, reasons=["No price history available."])

    ma50 = close.rolling(50).mean().iloc[-1] if len(close) >= 50 else close.iloc[-1]
    ma200 = close.rolling(200).mean().iloc[-1] if len(close) >= 200 else close.iloc[-1]
    trend = 0.0
    if ma50:
        trend += (close.iloc[-1] / ma50) - 1.0
    if ma200:
        trend += (close.iloc[-1] / ma200) - 1.0
    trend /= 2

    momentum = (_safe_return(close, 21) + _safe_return(close, 63)) / 2
    vol = float(close.pct_change().dropna().tail(20).std() * (252 ** 0.5)) if len(close.pct_change().dropna()) >= 20 else 0.0
    vol_penalty = max(0.0, vol - float(thresholds.get("volatility_high_threshold", 0.35)))
    score = float(trend + momentum - vol_penalty)

    bullish_threshold = float(thresholds.get("vams_bullish_threshold", 0.30))
    bearish_threshold = float(thresholds.get("vams_bearish_threshold", -0.30))
    if score >= bullish_threshold:
        state = "bullish"
    elif score <= bearish_threshold:
        state = "bearish"
    else:
        state = "neutral"

    reasons = [
        f"Trend score {trend:+.2f}.",
        f"Momentum score {momentum:+.2f}.",
        f"20D realized volatility {vol:.2f}.",
    ]
    return VamsSignal(
        symbol=symbol,
        state=state,
        score=score,
        volatility=vol,
        trend=float(trend),
        momentum=float(momentum),
        as_of=as_of.to_pydatetime() if isinstance(as_of, pd.Timestamp) else as_of,
        reasons=reasons,
    )


def get_vams_signals(client, symbols: list[str], thresholds: dict[str, float], force_refresh: bool = False) -> dict[str, VamsSignal]:
    return {
        symbol: get_vams_signal(client, symbol, thresholds, force_refresh=force_refresh)
        for symbol in symbols
    }
