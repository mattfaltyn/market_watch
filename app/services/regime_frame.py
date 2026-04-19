"""Shared regime composite time series (outer merge + forward-fill for stable live vs history alignment)."""

from __future__ import annotations

from typing import Any

import pandas as pd


def _close_series(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty or "close" not in frame.columns:
        return pd.DataFrame(columns=["report_date", "value"])
    result = frame[["report_date", "close"]].copy()
    result["value"] = pd.to_numeric(result["close"], errors="coerce")
    return result[["report_date", "value"]].dropna().sort_values("report_date")


def _trend_series(frame: pd.DataFrame, window: int) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame(columns=["report_date", "score"])
    result = frame.copy()
    result["score"] = result["value"] / result["value"].rolling(window).mean() - 1.0
    return result[["report_date", "score"]].dropna()


def _ratio_trend_series(client, numerator_symbol: str, denominator_symbol: str, force_refresh: bool = False) -> pd.DataFrame:
    ratio = client.get_price_ratio_history(numerator_symbol, denominator_symbol, force_refresh=force_refresh).data
    if ratio.empty:
        return pd.DataFrame(columns=["report_date", "score"])
    prepared = ratio.rename(columns={"ratio": "value"})
    return _trend_series(prepared, min(50, len(prepared.index) or 1))


def _yield_trend_series(client, column_name: str, force_refresh: bool = False) -> pd.DataFrame:
    result = client.get_yield_series(force_refresh=force_refresh).data
    if result.empty or column_name not in result.columns:
        return pd.DataFrame(columns=["report_date", "score"])
    frame = result[["report_date", column_name]].copy()
    frame["value"] = pd.to_numeric(frame[column_name], errors="coerce")
    frame["score"] = frame["value"] - frame["value"].shift(21)
    return frame[["report_date", "score"]].dropna()


def _classify_regime(growth_score: float, inflation_score: float) -> str:
    growth_direction = "up" if growth_score >= 0 else "down"
    inflation_direction = "up" if inflation_score >= 0 else "down"
    regime_map = {
        ("up", "down"): "goldilocks",
        ("up", "up"): "reflation",
        ("down", "up"): "inflation",
        ("down", "down"): "deflation",
    }
    return regime_map[(growth_direction, inflation_direction)]


def build_regime_composite_frame(client, config: Any, force_refresh: bool = False) -> pd.DataFrame:
    """Outer-merge proxy series, forward-fill, then composite scores (matches replay semantics)."""
    regime_inputs = config.regime_inputs
    growth_cfg = regime_inputs.get("growth", {})
    inflation_cfg = regime_inputs.get("inflation", {})

    equity = _trend_series(_close_series(client.get_prices(growth_cfg.get("equity_trend_symbol", "SPY"), force_refresh=force_refresh).data), 50).rename(
        columns={"score": "equity_trend"}
    )
    cyclical = _ratio_trend_series(client, growth_cfg.get("cyclical_symbol", "XLY"), growth_cfg.get("defensive_symbol", "XLP"), force_refresh=force_refresh).rename(
        columns={"score": "cyclical_defensive_ratio"}
    )
    copper = _ratio_trend_series(client, growth_cfg.get("copper_symbol", "CPER"), growth_cfg.get("gold_symbol", "GLD"), force_refresh=force_refresh).rename(
        columns={"score": "copper_gold_ratio"}
    )
    oil = _trend_series(_close_series(client.get_prices(inflation_cfg.get("oil_symbol", "USO"), force_refresh=force_refresh).data), 50).rename(columns={"score": "oil_trend"})
    commodity = _trend_series(_close_series(client.get_prices(inflation_cfg.get("commodity_symbol", "DBC"), force_refresh=force_refresh).data), 50).rename(
        columns={"score": "commodity_trend"}
    )
    yield_trend = _yield_trend_series(client, inflation_cfg.get("yield_symbol", "bc10_year"), force_refresh=force_refresh).rename(columns={"score": "yield_trend"})

    frames = [equity, cyclical, copper, oil, commodity, yield_trend]
    non_empty = [f for f in frames if not f.empty]
    if not non_empty:
        return pd.DataFrame(columns=["report_date", "growth_score", "inflation_score", "regime", "regime_strength"])

    merged = non_empty[0]
    for frame in non_empty[1:]:
        merged = merged.merge(frame, on="report_date", how="outer")
    merged = merged.sort_values("report_date")
    score_cols = [c for c in merged.columns if c != "report_date"]
    for col in score_cols:
        merged[col] = merged[col].ffill()

    growth_cols = [c for c in ("equity_trend", "cyclical_defensive_ratio", "copper_gold_ratio") if c in merged.columns]
    inflation_cols = [c for c in ("oil_trend", "commodity_trend", "yield_trend") if c in merged.columns]
    if not growth_cols or not inflation_cols:
        return pd.DataFrame(columns=["report_date", "growth_score", "inflation_score", "regime", "regime_strength"])

    merged["growth_score"] = merged[growth_cols].mean(axis=1)
    merged["inflation_score"] = merged[inflation_cols].mean(axis=1)
    merged = merged.dropna(subset=["growth_score", "inflation_score"])
    if merged.empty:  # pragma: no cover — degenerate numeric edge (all-NaN composite rows)
        return pd.DataFrame(columns=["report_date", "growth_score", "inflation_score", "regime", "regime_strength"])

    merged["regime"] = merged.apply(lambda row: _classify_regime(float(row["growth_score"]), float(row["inflation_score"])), axis=1)
    merged["regime_strength"] = merged[["growth_score", "inflation_score"]].abs().mean(axis=1)
    return merged
