from __future__ import annotations

import pandas as pd
from dash import html

from app.components.ui import app_shell, error_box, make_pie_chart, make_table
from app.models import KissPortfolioSnapshot


def render_implementation(snapshot: KissPortfolioSnapshot, errors: list[str]):
    rows = [
        {
            "Sleeve": sleeve.symbol,
            "Base": sleeve.base_weight,
            "Target": sleeve.target_weight,
            "Actual": sleeve.actual_weight,
            "Gap": sleeve.target_weight - sleeve.actual_weight,
            "VAMS": sleeve.vams_state.title(),
        }
        for sleeve in snapshot.sleeves
    ]
    rows.append(
        {
            "Sleeve": snapshot.cash_symbol,
            "Base": 0.0,
            "Target": 0.0,
            "Actual": snapshot.cash_weight,
            "Gap": snapshot.cash_weight,
            "VAMS": "n/a",
        }
    )
    return app_shell(
        [
            error_box(errors),
            html.Div(className="kpi-strip", children=[
                html.Div(className="section", children=[html.Div("Gross Exposure", className="metric-label"), html.Div(f"{snapshot.gross_exposure:.0%}", className="metric-value")]),
                html.Div(className="section", children=[html.Div("Cash", className="metric-label"), html.Div(f"{snapshot.cash_weight:.0%}", className="metric-value")]),
            ]),
            html.Div(className="two-col", children=[
                html.Div(className="section", children=[make_pie_chart([s.symbol for s in snapshot.sleeves], [s.target_weight for s in snapshot.sleeves], "Target Weights")]),
                html.Div(className="section", children=[make_pie_chart([s.symbol for s in snapshot.sleeves] + [snapshot.cash_symbol], [s.actual_weight for s in snapshot.sleeves] + [snapshot.cash_weight], "Actual Weights")]),
            ]),
            html.Div(className="section", children=[
                html.H3("Target vs Actual"),
                make_table(pd.DataFrame(rows), numeric_columns=["Base", "Target", "Actual", "Gap"]),
            ]),
        ],
        page_title="Target weights, actual weights, and implementation gaps.",
        active_page="implementation",
        status_meta={"as_of": snapshot.as_of, "scope": f"{snapshot.gross_exposure:.0%} invested"},
    )
