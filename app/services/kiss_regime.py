from __future__ import annotations

from statistics import mean

import pandas as pd

from app.models import KissRegime


def _latest_close(frame: pd.DataFrame) -> pd.Series:
    if frame.empty or "close" not in frame.columns:
        return pd.Series(dtype=float)
    return pd.to_numeric(frame.sort_values("report_date")["close"], errors="coerce").dropna()


def _trend_score(close: pd.Series, window: int) -> float:
    if len(close) < window:
        return 0.0
    moving_average = close.rolling(window).mean().iloc[-1]
    if moving_average == 0 or pd.isna(moving_average):
        return 0.0
    return float((close.iloc[-1] / moving_average) - 1.0)


def _ratio_trend(client, numerator_symbol: str, denominator_symbol: str, force_refresh: bool = False) -> tuple[float, pd.Timestamp | None]:
    num = client.get_prices(numerator_symbol, force_refresh=force_refresh).data
    den = client.get_prices(denominator_symbol, force_refresh=force_refresh).data
    if num.empty or den.empty:
        return 0.0, None
    merged = num[["report_date", "close"]].merge(
        den[["report_date", "close"]],
        on="report_date",
        suffixes=("_num", "_den"),
        how="inner",
    ).sort_values("report_date")
    if merged.empty:
        return 0.0, None
    ratio = pd.to_numeric(merged["close_num"], errors="coerce") / pd.to_numeric(merged["close_den"], errors="coerce")
    ratio = ratio.dropna()
    if ratio.empty:
        return 0.0, None
    as_of = merged["report_date"].max()
    return _trend_score(ratio, min(50, len(ratio))), as_of


def _yield_trend(client, column_name: str, force_refresh: bool = False) -> tuple[float, pd.Timestamp | None]:
    result = client.get_yield_series(force_refresh=force_refresh)
    frame = result.data.sort_values("report_date") if not result.data.empty else pd.DataFrame()
    if frame.empty or column_name not in frame.columns:
        return 0.0, None
    series = pd.to_numeric(frame[column_name], errors="coerce").dropna()
    if len(series) < 22:
        return 0.0, frame["report_date"].max()
    value = float(series.iloc[-1] - series.iloc[-22])
    return value, frame["report_date"].max()


def get_kiss_regime(client, config, force_refresh: bool = False) -> KissRegime:
    regime_inputs = config.regime_inputs
    growth_cfg = regime_inputs.get("growth", {})
    inflation_cfg = regime_inputs.get("inflation", {})
    weak_threshold = float(regime_inputs.get("weak_score_threshold", 0.10))

    equity_series = _latest_close(client.get_prices(growth_cfg.get("equity_trend_symbol", "SPY"), force_refresh=force_refresh).data)
    growth_components = {
        "equity_trend": _trend_score(equity_series, 50),
    }
    cyclical_score, cyclical_as_of = _ratio_trend(
        client,
        growth_cfg.get("cyclical_symbol", "XLY"),
        growth_cfg.get("defensive_symbol", "XLP"),
        force_refresh=force_refresh,
    )
    copper_score, copper_as_of = _ratio_trend(
        client,
        growth_cfg.get("copper_symbol", "CPER"),
        growth_cfg.get("gold_symbol", "GLD"),
        force_refresh=force_refresh,
    )
    growth_components["cyclical_defensive_ratio"] = cyclical_score
    growth_components["copper_gold_ratio"] = copper_score

    oil_series = _latest_close(client.get_prices(inflation_cfg.get("oil_symbol", "USO"), force_refresh=force_refresh).data)
    commodity_series = _latest_close(client.get_prices(inflation_cfg.get("commodity_symbol", "DBC"), force_refresh=force_refresh).data)
    yield_score, yield_as_of = _yield_trend(client, inflation_cfg.get("yield_symbol", "bc10_year"), force_refresh=force_refresh)
    inflation_components = {
        "oil_trend": _trend_score(oil_series, 50),
        "commodity_trend": _trend_score(commodity_series, 50),
        "yield_trend": yield_score,
    }

    growth_score = mean(growth_components.values()) if growth_components else 0.0
    inflation_score = mean(inflation_components.values()) if inflation_components else 0.0
    growth_direction = "up" if growth_score >= 0 else "down"
    inflation_direction = "up" if inflation_score >= 0 else "down"

    regime_map = {
        ("up", "down"): "goldilocks",
        ("up", "up"): "reflation",
        ("down", "up"): "inflation",
        ("down", "down"): "deflation",
    }
    regime = regime_map[(growth_direction, inflation_direction)]
    strength = mean([abs(growth_score), abs(inflation_score)])
    hybrid_label = None
    if abs(growth_score) < weak_threshold or abs(inflation_score) < weak_threshold:
        hybrid_label = f"{regime}-weak"

    reasons = [
        f"Growth proxies are trending {growth_direction}.",
        f"Inflation proxies are trending {inflation_direction}.",
        f"Composite scores: growth {growth_score:+.2f}, inflation {inflation_score:+.2f}.",
    ]
    as_of_candidates = [
        ts
        for ts in [
            cyclical_as_of,
            copper_as_of,
            yield_as_of,
            client.latest_timestamp([client.get_prices(growth_cfg.get('equity_trend_symbol', 'SPY'), force_refresh=force_refresh).data]),
        ]
        if ts is not None
    ]
    as_of = max(as_of_candidates) if as_of_candidates else None
    return KissRegime(
        regime=regime,
        regime_strength=float(strength),
        hybrid_label=hybrid_label,
        growth_direction=growth_direction,
        inflation_direction=inflation_direction,
        component_scores={**growth_components, **inflation_components},
        as_of=as_of.to_pydatetime() if isinstance(as_of, pd.Timestamp) else as_of,
        reasons=reasons,
    )
