from __future__ import annotations

import pandas as pd
from dash import html

from app.components.ui import (
    app_shell,
    badge,
    error_box,
    exposure_gauge,
    heatstrip,
    macro_quadrant,
    make_table,
    section_panel,
    signal_meter,
)
from app.models import KissRegime, VamsSignal


def _proxy_card(label: str, value: float) -> html.Div:
    tone = "positive" if value > 0 else "negative" if value < 0 else "neutral"
    return html.Div(
        className=f"sleeve-card tone-{tone if tone != 'neutral' else 'neutral_state'}",
        children=[
            html.Div(label.replace("_", " ").upper(), className="metric-label"),
            html.Div(f"{value:+.2f}", className="mini-stat-value"),
            signal_meter(value, -1.0, 1.0, "Score", "market" if value >= 0 else "negative"),
        ],
    )


def _vams_card(signal: VamsSignal) -> html.Div:
    tone = signal.state if signal.state != "neutral" else "neutral_state"
    return html.Div(
        className=f"sleeve-card tone-{tone}",
        children=[
            html.Div(className="sleeve-head", children=[html.Div(signal.symbol, className="sleeve-symbol"), badge(signal.state.upper(), signal.state)]),
            html.Div(f"{signal.score:+.2f}", className="sleeve-actual"),
            signal_meter(signal.trend or 0.0, -1.0, 1.0, "Trend", "market" if (signal.trend or 0.0) >= 0 else "negative"),
            signal_meter(signal.momentum or 0.0, -1.0, 1.0, "Momentum", "market" if (signal.momentum or 0.0) >= 0 else "negative"),
            signal_meter(signal.volatility or 0.0, 0.0, 1.0, "Volatility", "warning"),
            html.Div(" | ".join(signal.reasons[:2]) if signal.reasons else "No additional context", className="terminal-caption"),
        ],
    )


def render_signals(regime: KissRegime, vams_signals: dict[str, VamsSignal], errors: list[str]):
    growth_keys = [key for key in regime.component_scores if key in {"equity_trend", "cyclical_defensive_ratio", "copper_gold_ratio"}]
    inflation_keys = [key for key in regime.component_scores if key in {"oil_trend", "commodity_trend", "yield_trend"}]
    growth_score = sum(regime.component_scores[key] for key in growth_keys) / max(1, len(growth_keys))
    inflation_score = sum(regime.component_scores[key] for key in inflation_keys) / max(1, len(inflation_keys))

    vams_rows = pd.DataFrame(
        [
            {
                "Symbol": signal.symbol,
                "State": signal.state.upper(),
                "Score": signal.score,
                "Trend": signal.trend,
                "Momentum": signal.momentum,
                "Volatility": signal.volatility,
            }
            for signal in vams_signals.values()
        ]
    )
    regime_rows = pd.DataFrame([{"Component": key, "Score": value} for key, value in regime.component_scores.items()])

    sleeve_cards = [_vams_card(signal) for signal in vams_signals.values()]

    return app_shell(
        [
            error_box(errors),
            html.Div(
                className="two-col",
                children=[
                    section_panel(
                        "Quadrant Engine",
                        [
                            macro_quadrant(regime.regime, growth_score, inflation_score, regime.hybrid_label),
                            html.Div(className="chip-row", children=[badge(regime.growth_direction.upper(), "positive"), badge(regime.inflation_direction.upper(), "rates"), badge(regime.hybrid_label or "LOCKED", "warning" if regime.hybrid_label else "market")]),
                        ],
                        subtitle="Growth / inflation classifier",
                    ),
                    section_panel(
                        "Regime Strength",
                        [
                            html.Div(className="status-rail", children=[exposure_gauge(regime.regime_strength, "Strength", tone="market")]),
                            heatstrip(
                                [growth_score, inflation_score],
                                ["GROWTH", "INFLATION"],
                                {"GROWTH": "positive" if growth_score >= 0 else "negative", "INFLATION": "warning" if inflation_score >= 0 else "positive"},
                            ),
                        ],
                        subtitle="Composite signal balance",
                    ),
                ],
            ),
            section_panel(
                "Proxy Inputs",
                [html.Div(className="proxy-grid", children=[_proxy_card(key, value) for key, value in regime.component_scores.items()])],
                subtitle="Directional contributions",
            ),
            section_panel(
                "VAMS Diagnostics",
                [html.Div(className="signal-grid", children=sleeve_cards)],
                subtitle="Trend, momentum, volatility, state",
            ),
            html.Div(
                className="two-col",
                children=[
                    section_panel("Regime Components", [make_table(regime_rows, numeric_columns=["Score"])], subtitle="Raw scores"),
                    section_panel("VAMS Table", [make_table(vams_rows, numeric_columns=["Score", "Trend", "Momentum", "Volatility"])], subtitle="Secondary diagnostics"),
                ],
            ),
        ],
        page_title="Chart-first diagnostics for regime and sleeve state.",
        active_page="signals",
        status_meta={"as_of": regime.as_of, "scope": regime.regime.title()},
    )
