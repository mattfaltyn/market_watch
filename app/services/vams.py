from __future__ import annotations

import pandas as pd

from app.models import VamsHistoryPoint, VamsSignal


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


def _score_frame(frame: pd.DataFrame, thresholds: dict[str, float]) -> pd.DataFrame:
    if frame.empty or "close" not in frame.columns:
        return pd.DataFrame(columns=["report_date", "trend", "momentum", "volatility", "score", "state"])
    ordered = frame.sort_values("report_date").copy()
    ordered["close"] = pd.to_numeric(ordered["close"], errors="coerce")
    ordered = ordered.dropna(subset=["close"])
    if ordered.empty:
        return pd.DataFrame(columns=["report_date", "trend", "momentum", "volatility", "score", "state"])

    ma50 = ordered["close"].rolling(50).mean()
    ma200 = ordered["close"].rolling(200).mean()
    trend = (((ordered["close"] / ma50) - 1.0).fillna(0.0) + ((ordered["close"] / ma200) - 1.0).fillna(0.0)) / 2.0
    momentum = (((ordered["close"] / ordered["close"].shift(21)) - 1.0).fillna(0.0) + ((ordered["close"] / ordered["close"].shift(63)) - 1.0).fillna(0.0)) / 2.0
    volatility = ordered["close"].pct_change().rolling(20).std() * (252 ** 0.5)
    vol_penalty = (volatility - float(thresholds.get("volatility_high_threshold", 0.35))).clip(lower=0.0).fillna(0.0)
    score = (trend + momentum - vol_penalty).fillna(0.0)

    bullish_threshold = float(thresholds.get("vams_bullish_threshold", 0.30))
    bearish_threshold = float(thresholds.get("vams_bearish_threshold", -0.30))
    state = pd.Series("neutral", index=ordered.index)
    state = state.mask(score >= bullish_threshold, "bullish")
    state = state.mask(score <= bearish_threshold, "bearish")

    return pd.DataFrame(
        {
            "report_date": ordered["report_date"],
            "trend": trend,
            "momentum": momentum,
            "volatility": volatility,
            "score": score,
            "state": state,
        }
    ).dropna(subset=["report_date"])


def _fallback_scores(close: pd.Series) -> tuple[float, float, float]:
    ma50 = close.rolling(50).mean().iloc[-1] if len(close) >= 50 else close.iloc[-1]
    ma200 = close.rolling(200).mean().iloc[-1] if len(close) >= 200 else close.iloc[-1]
    trend = 0.0
    if ma50:
        trend += (close.iloc[-1] / ma50) - 1.0
    if ma200:
        trend += (close.iloc[-1] / ma200) - 1.0
    trend /= 2
    momentum = (_safe_return(close, 21) + _safe_return(close, 63)) / 2
    return float(trend), float(momentum), float(trend + momentum)


def get_vams_signal(client, symbol: str, thresholds: dict[str, float], force_refresh: bool = False) -> VamsSignal:
    result = client.get_prices(symbol, force_refresh=force_refresh)
    close, as_of = _latest_close(result.data)
    if close.empty:
        return VamsSignal(symbol=symbol, state="neutral", score=0.0, volatility=None, trend=None, momentum=None, as_of=None, reasons=["No price history available."])

    history = _score_frame(result.data, thresholds)
    latest = history.iloc[-1] if not history.empty else None
    fallback_trend, fallback_momentum, fallback_score = _fallback_scores(close)
    trend = float(latest["trend"]) if latest is not None else fallback_trend
    momentum = float(latest["momentum"]) if latest is not None else fallback_momentum
    vol = float(latest["volatility"]) if latest is not None and pd.notna(latest["volatility"]) else 0.0
    score = float(latest["score"]) if latest is not None else fallback_score
    state = str(latest["state"]) if latest is not None else "neutral"

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


def get_vams_signal_history(client, symbols: list[str], thresholds: dict[str, float], force_refresh: bool = False) -> dict[str, list[VamsHistoryPoint]]:
    history: dict[str, list[VamsHistoryPoint]] = {}
    for symbol in symbols:
        frame = client.get_prices(symbol, force_refresh=force_refresh).data
        scored = _score_frame(frame, thresholds)
        history[symbol] = [
            VamsHistoryPoint(
                date=row["report_date"].to_pydatetime() if isinstance(row["report_date"], pd.Timestamp) else row["report_date"],
                state=row["state"],
                score=float(row["score"]),
                trend=float(row["trend"]) if pd.notna(row["trend"]) else None,
                momentum=float(row["momentum"]) if pd.notna(row["momentum"]) else None,
                volatility=float(row["volatility"]) if pd.notna(row["volatility"]) else None,
            )
            for _, row in scored.iterrows()
        ]
    return history
