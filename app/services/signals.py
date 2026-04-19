from __future__ import annotations

from collections import Counter

import pandas as pd

from app.models import AlertFlag, MarketSnapshot, RatesSnapshot, RegimeSignal


def compute_regime(market: MarketSnapshot, rates: RatesSnapshot, watchlist: pd.DataFrame) -> RegimeSignal:
    score = 0
    reasons: list[str] = []

    above_trend = sum(1 for item in market.indices if item.ma50_state == "above" and item.ma200_state == "above")
    below_trend = sum(1 for item in market.indices if item.ma50_state == "below" and item.ma200_state == "below")

    if above_trend >= 2:
        score += 2
        reasons.append("major indices are above 50D and 200D trend")
    if below_trend >= 2:
        score -= 2
        reasons.append("major indices are below 50D and 200D trend")

    if market.positive_participation_ratio >= 0.75:
        score += 1
        reasons.append("most benchmarks are positive over 1M")
    elif market.positive_participation_ratio <= 0.25:
        score -= 1
        reasons.append("benchmark participation is weak")

    if rates.spread_10y_2y is not None and rates.spread_10y_2y < 0:
        score -= 1
        reasons.append("10Y-2Y curve is inverted")

    if rates.change_10y_1m is not None:
        if rates.change_10y_1m <= -0.0025:
            score += 1
            reasons.append("10Y yield has fallen over the last month")
        elif rates.change_10y_1m >= 0.0025:
            score -= 1
            reasons.append("10Y yield has risen over the last month")

    if not watchlist.empty and "return_1m" in watchlist.columns:
        positive_watchlist_ratio = (watchlist["return_1m"].fillna(0) > 0).mean()
        if positive_watchlist_ratio >= 0.6:
            score += 1
            reasons.append("watchlist participation is constructive")
        elif positive_watchlist_ratio <= 0.4:
            score -= 1
            reasons.append("watchlist participation is weak")

    if score >= 2:
        regime = "Risk-On"
    elif score <= -2:
        regime = "Risk-Off"
    else:
        regime = "Neutral"
    return RegimeSignal(regime=regime, score=score, reasons=reasons[:3])


def get_alert_flags(
    symbol: str,
    watchlist_row: pd.Series,
    rates: RatesSnapshot,
    thresholds: dict[str, float],
) -> list[AlertFlag]:
    flags: list[AlertFlag] = []
    move_threshold = float(thresholds.get("large_move_1d", 0.03))
    valuation_band = float(thresholds.get("valuation_industry_gap", 0.2))

    earnings_days = watchlist_row.get("days_to_earnings")
    if pd.notna(earnings_days) and earnings_days <= 14:
        flags.append(AlertFlag(symbol, "earnings", f"Earnings in {int(earnings_days)} days", "high"))

    return_1d = watchlist_row.get("return_1d")
    if pd.notna(return_1d) and abs(return_1d) >= move_threshold:
        flags.append(AlertFlag(symbol, "price_move", f"1D move {return_1d:.1%}", "medium"))

    ma50_state = watchlist_row.get("ma50_state")
    ma200_state = watchlist_row.get("ma200_state")
    if ma50_state == "below" and ma200_state == "below":
        flags.append(AlertFlag(symbol, "trend", "Price is below 50D and 200D trend", "medium"))

    pe_gap = watchlist_row.get("ttm_pe_vs_industry")
    if pd.notna(pe_gap) and abs(pe_gap) >= valuation_band:
        direction = "above" if pe_gap > 0 else "below"
        flags.append(AlertFlag(symbol, "valuation", f"TTM P/E is {direction} industry by {abs(pe_gap):.0%}", "medium"))

    net_margin = watchlist_row.get("net_margin")
    revenue_growth = watchlist_row.get("revenue_yoy_growth")
    if pd.notna(net_margin) and net_margin < 0:
        flags.append(AlertFlag(symbol, "quality", "Net margin is negative", "high"))
    if pd.notna(revenue_growth) and revenue_growth < 0:
        flags.append(AlertFlag(symbol, "growth", "Revenue growth is negative", "high"))

    if rates.spread_10y_2y is not None and rates.spread_10y_2y < 0:
        flags.append(AlertFlag(symbol, "macro", "Yield curve is inverted", "low"))

    return flags


def summarize_alerts(rows: pd.DataFrame) -> dict[str, int]:
    if rows.empty or "alert_count" not in rows.columns:
        return {"high_alerts": 0, "medium_alerts": 0, "total_alerts": 0}
    return {
        "high_alerts": int(rows.get("high_alert_count", pd.Series(dtype=int)).fillna(0).sum()),
        "medium_alerts": int(rows.get("medium_alert_count", pd.Series(dtype=int)).fillna(0).sum()),
        "total_alerts": int(rows["alert_count"].fillna(0).sum()),
    }
