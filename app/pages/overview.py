from __future__ import annotations

from dash import html
import pandas as pd

from app.components.ui import (
    SLEEVE_COLORS,
    allocation_band,
    app_shell,
    badge,
    delta_strip,
    error_box,
    exposure_gauge,
    heatstrip,
    macro_quadrant,
    make_table,
    metric_card,
    section_panel,
    sleeve_state_card,
    stat_chip,
)
from app.models import KissPortfolioSnapshot, MetricCard, VamsSignal


def _proxy_scores(snapshot: KissPortfolioSnapshot) -> tuple[float, float]:
    growth_keys = [key for key in snapshot.regime.component_scores if key in {"equity_trend", "cyclical_defensive_ratio", "copper_gold_ratio"}]
    inflation_keys = [key for key in snapshot.regime.component_scores if key in {"oil_trend", "commodity_trend", "yield_trend"}]
    growth_score = sum(snapshot.regime.component_scores[key] for key in growth_keys) / max(1, len(growth_keys))
    inflation_score = sum(snapshot.regime.component_scores[key] for key in inflation_keys) / max(1, len(inflation_keys))
    return float(growth_score), float(inflation_score)


def _latest_signal_caption(snapshot: KissPortfolioSnapshot) -> str:
    if not snapshot.signal_changes:
        return "NO CHANGE"
    change = snapshot.signal_changes[0]
    return f"{change.symbol} {change.field.replace('_', ' ').upper()}"


def _action_items(snapshot: KissPortfolioSnapshot) -> list[str]:
    items: list[str] = []
    for sleeve in snapshot.sleeves:
        gap = sleeve.target_weight - sleeve.actual_weight
        if gap > 0:
            items.append(f"Increase {sleeve.symbol} to {sleeve.target_weight:.0%}")
        elif gap < 0:
            items.append(f"Trim {sleeve.symbol} to {sleeve.target_weight:.0%}")
        else:
            items.append(f"Hold {sleeve.symbol} at {sleeve.actual_weight:.0%}")
    items.append(f"Keep {snapshot.cash_weight:.0%} in {snapshot.cash_symbol}")
    return items[:4]


def _table_frame(snapshot: KissPortfolioSnapshot) -> pd.DataFrame:
    rows = [
        {
            "Sleeve": sleeve.symbol,
            "Base": sleeve.base_weight,
            "Target": sleeve.target_weight,
            "Actual": sleeve.actual_weight,
            "Delta": sleeve.delta_from_prior,
            "VAMS": sleeve.vams_state.upper(),
        }
        for sleeve in snapshot.sleeves
    ]
    rows.append({"Sleeve": snapshot.cash_symbol, "Base": 0.0, "Target": 0.0, "Actual": snapshot.cash_weight, "Delta": None, "VAMS": "CASH"})
    return pd.DataFrame(rows)


def render_kiss_overview(snapshot: KissPortfolioSnapshot, errors: list[str]):
    growth_score, inflation_score = _proxy_scores(snapshot)

    labels = [s.symbol for s in snapshot.sleeves] + [snapshot.cash_symbol]
    base = [s.base_weight for s in snapshot.sleeves] + [0.0]
    target = [s.target_weight for s in snapshot.sleeves] + [0.0]
    actual = [s.actual_weight for s in snapshot.sleeves] + [snapshot.cash_weight]

    kpis = [
        MetricCard("Regime", snapshot.regime.regime.title(), f"Strength {snapshot.regime.regime_strength:.2f}", tone="market", icon="◫", emphasis="high"),
        MetricCard("Gross Exposure", f"{snapshot.gross_exposure:.0%}", "Risk allocated", tone="positive" if snapshot.gross_exposure >= 0.6 else "warning", icon="◎", sparkline=[0.3, 0.5, snapshot.gross_exposure]),
        MetricCard("Cash", f"{snapshot.cash_weight:.0%}", snapshot.cash_symbol, tone="warning" if snapshot.cash_weight > 0.2 else "positive", icon="◌", sparkline=[0.5, 0.4, snapshot.cash_weight]),
        MetricCard("Latest Event", _latest_signal_caption(snapshot), snapshot.signal_changes[0].message if snapshot.signal_changes else "Stable session", tone="warning", icon="↻"),
        MetricCard("Action", "IMPLEMENT", snapshot.implementation_text.split(";")[0], tone="market", icon="→"),
    ]

    sleeve_cards = [sleeve_state_card(sleeve, VamsSignal(sleeve.symbol, sleeve.vams_state, 0.0, None, None, None, snapshot.as_of, [])) for sleeve in snapshot.sleeves]
    cash_sleeve = snapshot.sleeves[0]
    sleeve_cards.append(
        sleeve_state_card(
            type(cash_sleeve)(
                name="cash",
                symbol=snapshot.cash_symbol,
                base_weight=0.0,
                target_weight=0.0,
                actual_weight=snapshot.cash_weight,
                vams_state="neutral",
                vams_multiplier=1.0,
                regime_rule_applied=snapshot.regime.regime.title(),
                delta_from_prior=None,
            ),
            VamsSignal(snapshot.cash_symbol, "neutral", 0.0, None, None, None, snapshot.as_of, []),
        )
    )

    return app_shell(
        [
            error_box(errors),
            html.Div(className="kpi-strip", children=[metric_card(card) for card in kpis]),
            html.Div(
                className="hero-grid",
                children=[
                    section_panel(
                        "Macro State",
                        [
                            macro_quadrant(snapshot.regime.regime, growth_score, inflation_score, snapshot.regime.hybrid_label),
                            heatstrip(
                                list(snapshot.regime.component_scores.values()),
                                [key.replace("_", " ").upper() for key in snapshot.regime.component_scores.keys()],
                            ),
                        ],
                        subtitle="Growth / inflation quadrant",
                    ),
                    section_panel(
                        "Implemented Allocation",
                        [
                            html.Div(className="status-rail", children=[
                                exposure_gauge(snapshot.gross_exposure, "Gross"),
                                exposure_gauge(snapshot.cash_weight, "Cash", tone="warning"),
                            ]),
                            allocation_band(base, target, actual, labels, SLEEVE_COLORS),
                            html.Div(className="chip-row", children=[badge(snapshot.regime.growth_direction.upper(), "positive"), badge(snapshot.regime.inflation_direction.upper(), "rates"), stat_chip("Action", "LIVE", "market")]),
                        ],
                        subtitle="Base / target / actual",
                    ),
                ],
            ),
            section_panel("Sleeve State Board", html.Div(className="sleeve-grid", children=sleeve_cards), subtitle="Target, actual, VAMS, delta"),
            html.Div(
                className="two-col",
                children=[
                    section_panel("Change Rail", [delta_strip(snapshot.signal_changes)], subtitle="Current session events"),
                    section_panel(
                        "Action Now",
                        [
                            html.Div(className="action-list", children=[html.Div(item, className="action-item") for item in _action_items(snapshot)]),
                            html.Div(snapshot.summary_text, className="terminal-caption"),
                        ],
                        subtitle="Implementation cues",
                    ),
                ],
            ),
            section_panel(
                "Audit Table",
                [make_table(_table_frame(snapshot), numeric_columns=["Base", "Target", "Actual", "Delta"])],
                subtitle="Secondary numeric view",
            ),
        ],
        page_title="Portfolio state board for the current KISS regime.",
        active_page="kiss-overview",
        status_meta={"as_of": snapshot.as_of, "scope": snapshot.regime.regime.title()},
    )
