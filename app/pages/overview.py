from __future__ import annotations

from dash import html

from app.components.ui import app_shell, badge, error_box, insight_list, make_pie_chart, make_table, metric_card
from app.models import KissPortfolioSnapshot, MetricCard


def _signal_change_items(snapshot: KissPortfolioSnapshot) -> list[str]:
    if not snapshot.signal_changes:
        return ["No signal changes since the last in-session snapshot."]
    return [change.message for change in snapshot.signal_changes[:5]]


def render_kiss_overview(snapshot: KissPortfolioSnapshot, errors: list[str]):
    last_change = snapshot.signal_changes[0].message if snapshot.signal_changes else "No change detected in this session."
    cards = [
        MetricCard("Current Regime", snapshot.regime.regime.title(), f"Strength {snapshot.regime.regime_strength:.2f}", "neutral", "kpi"),
        MetricCard("Portfolio Action", f"{snapshot.gross_exposure:.0%} Risk Allocated", snapshot.implementation_text, "market", "kpi"),
        MetricCard("Last Signal Change", last_change, "Current session delta", "warning", "kpi"),
        MetricCard("Implementation Status", f"{snapshot.cash_weight:.0%} Cash", snapshot.summary_text, "positive" if snapshot.cash_weight <= 0.35 else "neutral", "kpi"),
    ]

    rows = []
    for sleeve in snapshot.sleeves:
        rows.append(
            {
                "Sleeve": sleeve.symbol,
                "Base": sleeve.base_weight,
                "Target": sleeve.target_weight,
                "VAMS": sleeve.vams_state.title(),
                "Actual": sleeve.actual_weight,
                "Delta": sleeve.delta_from_prior,
            }
        )
    rows.append(
        {
            "Sleeve": snapshot.cash_symbol,
            "Base": 0.0,
            "Target": 0.0,
            "VAMS": "n/a",
            "Actual": snapshot.cash_weight,
            "Delta": None,
        }
    )

    target_labels = [s.symbol for s in snapshot.sleeves]
    target_values = [s.target_weight for s in snapshot.sleeves]
    actual_labels = [s.symbol for s in snapshot.sleeves] + [snapshot.cash_symbol]
    actual_values = [s.actual_weight for s in snapshot.sleeves] + [snapshot.cash_weight]

    return app_shell(
        [
            error_box(errors),
            html.Div(className="hero-grid", children=[
                html.Div(className="section hero-card tone-neutral", children=[
                    html.Div("KISS State", className="hero-label"),
                    html.Div(snapshot.regime.regime.title(), className="hero-value"),
                    html.Div(
                        f"Growth is {snapshot.regime.growth_direction}; inflation is {snapshot.regime.inflation_direction}. "
                        + (snapshot.regime.hybrid_label or "Classification confidence is acceptable."),
                        className="hero-summary",
                    ),
                    html.Div(className="hero-footer", children=[
                        badge(f"Gross {snapshot.gross_exposure:.0%}", "market"),
                        badge(f"Cash {snapshot.cash_weight:.0%}", "neutral"),
                    ]),
                ]),
                insight_list(
                    [
                        snapshot.summary_text,
                        snapshot.implementation_text,
                        f"Regime reasons: {' '.join(snapshot.regime.reasons[:2])}",
                    ],
                    "What To Implement Now",
                ),
            ]),
            html.Div(className="kpi-strip", children=[metric_card(card) for card in cards]),
            html.Div(className="two-col", children=[
                html.Div(className="section", children=[make_pie_chart(target_labels, target_values, "Target Allocation")]),
                html.Div(className="section", children=[make_pie_chart(actual_labels, actual_values, "Implemented Allocation")]),
            ]),
            html.Div(className="two-col", children=[
                html.Div(className="section", children=[
                    html.H3("Sleeve Implementation"),
                    make_table(
                        __import__("pandas").DataFrame(rows),
                        numeric_columns=["Base", "Target", "Actual", "Delta"],
                    ),
                ]),
                insight_list(_signal_change_items(snapshot), "What Changed?"),
            ]),
        ],
        page_title="What should the portfolio be right now?",
        active_page="kiss-overview",
        status_meta={"as_of": snapshot.as_of, "scope": snapshot.regime.regime.title()},
    )
