from __future__ import annotations

import pandas as pd

from app.models import KissRegime
from app.services.regime_frame import build_regime_composite_frame


def get_kiss_regime(client, config, force_refresh: bool = False) -> KissRegime:
    regime_inputs = config.regime_inputs
    weak_threshold = float(regime_inputs.get("weak_score_threshold", 0.10))

    frame = build_regime_composite_frame(client, config, force_refresh=force_refresh)
    empty_keys = ("equity_trend", "cyclical_defensive_ratio", "copper_gold_ratio", "oil_trend", "commodity_trend", "yield_trend")
    if frame.empty:
        return KissRegime(
            regime="deflation",
            regime_strength=0.0,
            hybrid_label=None,
            growth_direction="down",
            inflation_direction="down",
            component_scores={k: None for k in empty_keys},
            as_of=None,
            reasons=["Insufficient overlapping history to classify regime."],
            unavailable_components=list(empty_keys),
        )

    last = frame.iloc[-1]
    growth_score = float(last["growth_score"])
    inflation_score = float(last["inflation_score"])
    regime = str(last["regime"])
    strength = float(last["regime_strength"])
    growth_direction = "up" if growth_score >= 0 else "down"
    inflation_direction = "up" if inflation_score >= 0 else "down"

    component_scores: dict[str, float | None] = {}
    for key in ("equity_trend", "cyclical_defensive_ratio", "copper_gold_ratio", "oil_trend", "commodity_trend", "yield_trend"):
        if key in last.index:
            val = last[key]
            component_scores[key] = float(val) if pd.notna(val) else None
        else:
            component_scores[key] = None

    unavailable_components = [name for name, val in component_scores.items() if val is None]
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
            f"Some inputs missing on latest row: {', '.join(unavailable_components)}."
        )

    as_of = pd.Timestamp(last["report_date"]).to_pydatetime()

    return KissRegime(
        regime=regime,
        regime_strength=float(strength),
        hybrid_label=hybrid_label,
        growth_direction=growth_direction,
        inflation_direction=inflation_direction,
        component_scores=component_scores,
        as_of=as_of,
        reasons=reasons,
        unavailable_components=unavailable_components,
    )
