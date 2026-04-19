from __future__ import annotations

import pandas as pd
from dash import html

from app.components.ui import (
    app_shell,
    badge,
    error_box,
    heatstrip,
    macro_quadrant,
    make_line_chart,
    make_table,
    section_panel,
    signal_meter,
    transition_strip,
)
from app.models import RegimeOverviewSnapshot


def _history_frame(snapshot: RegimeOverviewSnapshot) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "report_date": point.date,
                "growth_score": point.growth_score,
                "inflation_score": point.inflation_score,
                "regime_strength": point.regime_strength,
            }
            for point in snapshot.regime_history
        ]
    )


def render_signals(snapshot: RegimeOverviewSnapshot, errors: list[str]):
    regime = snapshot.regime
    growth_score = snapshot.regime_history[-1].growth_score if snapshot.regime_history else 0.0
    inflation_score = snapshot.regime_history[-1].inflation_score if snapshot.regime_history else 0.0
    history_frame = _history_frame(snapshot)

    proxy_rows = pd.DataFrame(
        [{"Component": key, "Score": value} for key, value in regime.component_scores.items()]
    )
    confirmation_rows = pd.DataFrame(
        [
            {
                "Symbol": confirmation.symbol,
                "Role": confirmation.role_label,
                "State": confirmation.state.upper(),
                "Score": confirmation.score,
                "Trend": confirmation.trend,
                "Momentum": confirmation.momentum,
                "Volatility": confirmation.volatility,
            }
            for confirmation in snapshot.confirmations
        ]
    )

    confirmation_cards = []
    for confirmation in snapshot.confirmations:
        confirmation_cards.append(
            html.Div(
                className=f"sleeve-card tone-{confirmation.state if confirmation.state != 'neutral' else 'neutral_state'}",
                children=[
                    html.Div(className="sleeve-head", children=[html.Div(confirmation.symbol, className="sleeve-symbol"), badge(confirmation.state.upper(), confirmation.state)]),
                    html.Div(confirmation.role_label, className="terminal-caption"),
                    signal_meter(confirmation.score, -1.0, 1.0, "Score", "market" if confirmation.score >= 0 else "negative"),
                    signal_meter(confirmation.trend or 0.0, -1.0, 1.0, "Trend", "market" if (confirmation.trend or 0.0) >= 0 else "negative"),
                    signal_meter(confirmation.momentum or 0.0, -1.0, 1.0, "Momentum", "market" if (confirmation.momentum or 0.0) >= 0 else "negative"),
                    signal_meter(confirmation.volatility or 0.0, 0.0, 1.0, "Volatility", "warning"),
                ],
            )
        )

    return app_shell(
        [
            error_box(errors),
            html.Div(
                className="two-col",
                children=[
                    section_panel(
                        "Quadrant",
                        [macro_quadrant(regime.regime, growth_score, inflation_score, regime.hybrid_label)],
                        subtitle="Current regime classifier",
                    ),
                    section_panel(
                        "Transitions",
                        [transition_strip(snapshot.transitions)],
                        subtitle="Derived from Yahoo Finance history",
                    ),
                ],
            ),
            html.Div(
                className="two-col",
                children=[
                    section_panel(
                        "Regime History",
                        [make_line_chart(history_frame, "report_date", ["growth_score", "inflation_score"], "Growth vs Inflation", semantic="market")],
                        subtitle="Historical score replay",
                    ),
                    section_panel(
                        "Regime Strength",
                        [make_line_chart(history_frame, "report_date", ["regime_strength"], "Strength", semantic="rates")],
                        subtitle="Confidence over time",
                    ),
                ],
            ),
            html.Div(
                className="two-col",
                children=[
                    section_panel(
                        "Growth Decomposition",
                        [heatstrip([regime.component_scores.get("equity_trend"), regime.component_scores.get("cyclical_defensive_ratio"), regime.component_scores.get("copper_gold_ratio")], ["EQUITY", "CYCLICAL", "COPPER/GOLD"])],
                    ),
                    section_panel(
                        "Inflation Decomposition",
                        [heatstrip([regime.component_scores.get("oil_trend"), regime.component_scores.get("commodity_trend"), regime.component_scores.get("yield_trend")], ["OIL", "COMMODITY", "10Y YIELD"])],
                    ),
                ],
            ),
            section_panel("Confirmation Signals", [html.Div(className="signal-grid", children=confirmation_cards)], subtitle="VAMS confirmation history and state"),
            html.Div(
                className="two-col",
                children=[
                    section_panel("Regime Components", [make_table(proxy_rows, numeric_columns=["Score"])], subtitle="Raw proxy scores"),
                    section_panel("Confirmation Table", [make_table(confirmation_rows, numeric_columns=["Score", "Trend", "Momentum", "Volatility"])], subtitle="Secondary diagnostics"),
                ],
            ),
        ],
        page_title="Why the model is calling the current regime.",
        active_page="signals",
        status_meta={"as_of": snapshot.as_of, "scope": regime.regime.title()},
    )
