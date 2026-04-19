from __future__ import annotations

from statistics import mean

import pandas as pd

from app.models import KissRegime


def _latest_close(frame: pd.DataFrame) -> pd.Series:
    if frame.empty or "close" not in frame.columns:
        return pd.Series(dtype=float)
    return pd.to_numeric(frame.sort_values("report_date")["close"], errors="coerce").dropna()


def _trend_score_optional(close: pd.Series, window: int) -> float | None:
    if len(close) < window:
        return None
    moving_average = close.rolling(window).mean().iloc[-1]
    if moving_average == 0 or pd.isna(moving_average):
        return None
    return float((close.iloc[-1] / moving_average) - 1.0)


def _ratio_trend(
    client, numerator_symbol: str, denominator_symbol: str, force_refresh: bool = False
) -> tuple[float | None, pd.Timestamp | None]:
    num = client.get_prices(numerator_symbol, force_refresh=force_refresh).data
    den = client.get_prices(denominator_symbol, force_refresh=force_refresh).data
    if num.empty or den.empty:
        return None, None
    merged = num[["report_date", "close"]].merge(
        den[["report_date", "close"]],
        on="report_date",
        suffixes=("_num", "_den"),
        how="inner",
    ).sort_values("report_date")
    if merged.empty:
        return None, None
    ratio = pd.to_numeric(merged["close_num"], errors="coerce") / pd.to_numeric(merged["close_den"], errors="coerce")
    ratio = ratio.dropna()
    if ratio.empty:
        return None, None
    as_of = merged["report_date"].max()
    score = _trend_score_optional(ratio, min(50, len(ratio)))
    return score, as_of


def _yield_trend(client, column_name: str, force_refresh: bool = False) -> tuple[float | None, pd.Timestamp | None]:
    result = client.get_yield_series(force_refresh=force_refresh)
    frame = result.data.sort_values("report_date") if not result.data.empty else pd.DataFrame()
    if frame.empty or column_name not in frame.columns:
        return None, None
    series = pd.to_numeric(frame[column_name], errors="coerce").dropna()
    if len(series) < 22:
        return None, frame["report_date"].max() if "report_date" in frame.columns else None
    value = float(series.iloc[-1] - series.iloc[-22])
    return value, frame["report_date"].max()


def _mean_present(values: list[float | None]) -> float:
    present = [v for v in values if v is not None]
    return float(mean(present)) if present else 0.0


def get_kiss_regime(client, config, force_refresh: bool = False) -> KissRegime:
    regime_inputs = config.regime_inputs
    growth_cfg = regime_inputs.get("growth", {})
    inflation_cfg = regime_inputs.get("inflation", {})
    weak_threshold = float(regime_inputs.get("weak_score_threshold", 0.10))

    equity_series = _latest_close(client.get_prices(growth_cfg.get("equity_trend_symbol", "SPY"), force_refresh=force_refresh).data)
    equity_trend = _trend_score_optional(equity_series, 50)

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

    oil_series = _latest_close(client.get_prices(inflation_cfg.get("oil_symbol", "USO"), force_refresh=force_refresh).data)
    commodity_series = _latest_close(client.get_prices(inflation_cfg.get("commodity_symbol", "DBC"), force_refresh=force_refresh).data)
    yield_score, yield_as_of = _yield_trend(client, inflation_cfg.get("yield_symbol", "bc10_year"), force_refresh=force_refresh)

    component_scores: dict[str, float | None] = {
        "equity_trend": equity_trend,
        "cyclical_defensive_ratio": cyclical_score,
        "copper_gold_ratio": copper_score,
        "oil_trend": _trend_score_optional(oil_series, 50),
        "commodity_trend": _trend_score_optional(commodity_series, 50),
        "yield_trend": yield_score,
    }
    unavailable_components = [name for name, val in component_scores.items() if val is None]

    growth_vals: list[float | None] = [equity_trend, cyclical_score, copper_score]
    inflation_vals: list[float | None] = [
        component_scores["oil_trend"],
        component_scores["commodity_trend"],
        yield_score,
    ]
    growth_score = _mean_present(growth_vals)
    inflation_score = _mean_present(inflation_vals)

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
    if unavailable_components:
        reasons.append(
            f"Unavailable regime inputs (excluded from composite mean): {', '.join(unavailable_components)}."
        )

    as_of_candidates = [
        ts
        for ts in [
            cyclical_as_of,
            copper_as_of,
            yield_as_of,
            client.latest_timestamp([client.get_prices(growth_cfg.get("equity_trend_symbol", "SPY"), force_refresh=force_refresh).data]),
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
        component_scores=component_scores,
        as_of=as_of.to_pydatetime() if isinstance(as_of, pd.Timestamp) else as_of,
        reasons=reasons,
        unavailable_components=unavailable_components,
    )
