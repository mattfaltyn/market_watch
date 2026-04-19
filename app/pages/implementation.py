from __future__ import annotations

import pandas as pd
from dash import html

from app.components.ui import (
    SLEEVE_COLORS,
    allocation_band,
    app_shell,
    error_box,
    exposure_gauge,
    make_table,
    section_panel,
    sleeve_state_card,
)
from app.models import KissPortfolioSnapshot, SleeveAllocation, VamsSignal


def _action_rows(snapshot: KissPortfolioSnapshot) -> list[str]:
    rows: list[str] = []
    for sleeve in snapshot.sleeves:
        gap = sleeve.target_weight - sleeve.actual_weight
        if gap > 0:
            rows.append(f"Increase {sleeve.symbol} by {gap:.0%}")
        elif gap < 0:
            rows.append(f"Reduce {sleeve.symbol} by {abs(gap):.0%}")
        else:
            rows.append(f"Hold {sleeve.symbol} at target")
    rows.append(f"Remain {snapshot.cash_weight:.0%} in {snapshot.cash_symbol}")
    return rows


def _gap_frame(snapshot: KissPortfolioSnapshot) -> pd.DataFrame:
    rows = [
        {
            "Sleeve": sleeve.symbol,
            "Base": sleeve.base_weight,
            "Target": sleeve.target_weight,
            "Actual": sleeve.actual_weight,
            "Gap": sleeve.target_weight - sleeve.actual_weight,
            "VAMS": sleeve.vams_state.upper(),
        }
        for sleeve in snapshot.sleeves
    ]
    rows.append({"Sleeve": snapshot.cash_symbol, "Base": 0.0, "Target": 0.0, "Actual": snapshot.cash_weight, "Gap": snapshot.cash_weight, "VAMS": "CASH"})
    return pd.DataFrame(rows)


def render_implementation(snapshot: KissPortfolioSnapshot, errors: list[str]):
    labels = [s.symbol for s in snapshot.sleeves] + [snapshot.cash_symbol]
    base = [s.base_weight for s in snapshot.sleeves] + [0.0]
    target = [s.target_weight for s in snapshot.sleeves] + [0.0]
    actual = [s.actual_weight for s in snapshot.sleeves] + [snapshot.cash_weight]

    sleeve_cards = [
        sleeve_state_card(sleeve, VamsSignal(sleeve.symbol, sleeve.vams_state, 0.0, None, None, None, snapshot.as_of, []))
        for sleeve in snapshot.sleeves
    ]
    sleeve_cards.append(
        sleeve_state_card(
            SleeveAllocation("cash", snapshot.cash_symbol, 0.0, 0.0, snapshot.cash_weight, "neutral", 1.0, snapshot.regime.regime.title(), None),
            VamsSignal(snapshot.cash_symbol, "neutral", 0.0, None, None, None, snapshot.as_of, []),
        )
    )

    return app_shell(
        [
            error_box(errors),
            html.Div(
                className="status-rail",
                children=[
                    section_panel("Exposure", [exposure_gauge(snapshot.gross_exposure, "Invested", tone="positive")], subtitle="Gross risk"),
                    section_panel("Cash", [exposure_gauge(snapshot.cash_weight, snapshot.cash_symbol, tone="warning")], subtitle="Residual allocation"),
                ],
            ),
            section_panel(
                "Allocation Bands",
                [allocation_band(base, target, actual, labels, SLEEVE_COLORS)],
                subtitle="Base / target / actual",
            ),
            html.Div(
                className="two-col",
                children=[
                    section_panel(
                        "Implementation Gaps",
                        [html.Div(className="action-list", children=[html.Div(item, className="action-item") for item in _action_rows(snapshot)])],
                        subtitle="Actionable gap view",
                    ),
                    section_panel(
                        "State Cards",
                        [html.Div(className="sleeve-grid", children=sleeve_cards)],
                        subtitle="Sleeve-by-sleeve implementation",
                    ),
                ],
            ),
            section_panel(
                "Target vs Actual",
                [make_table(_gap_frame(snapshot), numeric_columns=["Base", "Target", "Actual", "Gap"])],
                subtitle="Secondary numeric view",
            ),
        ],
        page_title="Allocation workspace for target vs actual portfolio state.",
        active_page="implementation",
        status_meta={"as_of": snapshot.as_of, "scope": f"{snapshot.gross_exposure:.0%} invested"},
    )
