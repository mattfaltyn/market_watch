from __future__ import annotations

import pandas as pd
from dash import html

from app.components.ui import app_shell, error_box, make_table, metric_card
from app.models import KissRegime, MetricCard, VamsSignal


def render_signals(regime: KissRegime, vams_signals: dict[str, VamsSignal], errors: list[str]):
    cards = [
        MetricCard("Growth Direction", regime.growth_direction.title(), f"Strength {regime.component_scores.get('equity_trend', 0.0):+.2f}", "market", "compact"),
        MetricCard("Inflation Direction", regime.inflation_direction.title(), f"Strength {regime.component_scores.get('yield_trend', 0.0):+.2f}", "rates", "compact"),
        MetricCard("Quadrant", regime.regime.title(), regime.hybrid_label or "No hybrid override", "neutral", "compact"),
    ]
    vams_rows = [
        {
            "Symbol": signal.symbol,
            "State": signal.state.title(),
            "Score": signal.score,
            "Trend": signal.trend,
            "Momentum": signal.momentum,
            "Volatility": signal.volatility,
        }
        for signal in vams_signals.values()
    ]
    regime_rows = pd.DataFrame(
        [{"Component": key, "Score": value} for key, value in regime.component_scores.items()]
    )
    return app_shell(
        [
            error_box(errors),
            html.Div(className="kpi-strip", children=[metric_card(card) for card in cards]),
            html.Div(className="two-col", children=[
                html.Div(className="section", children=[html.H3("Growth & Inflation Inputs"), make_table(regime_rows, numeric_columns=["Score"])]),
                html.Div(className="section", children=[html.H3("Regime Reasons"), html.Ul(className="insight-list", children=[html.Li(reason) for reason in regime.reasons])]),
            ]),
            html.Div(className="section", children=[
                html.H3("VAMS Diagnostics"),
                make_table(pd.DataFrame(vams_rows), numeric_columns=["Score", "Trend", "Momentum", "Volatility"]),
            ]),
        ],
        page_title="Macro regime diagnostics and per-sleeve VAMS states.",
        active_page="signals",
        status_meta={"as_of": regime.as_of, "scope": regime.regime.title()},
    )
