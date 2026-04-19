from __future__ import annotations

import pandas as pd
from dash import html

from app.components.ui import (
    app_shell,
    badge,
    benchmark_card,
    error_box,
    heatstrip,
    macro_quadrant,
    metric_card,
    section_panel,
    signal_meter,
    stat_chip,
    transition_strip,
)
from app.models import IndicatorSnapshot, MetricCard, RegimeOverviewSnapshot


def _indicator_map(snapshot: RegimeOverviewSnapshot) -> dict[str, IndicatorSnapshot]:
    return {indicator.symbol: indicator for indicator in snapshot.indicators}


def _benchmark_tiles(snapshot: RegimeOverviewSnapshot) -> list[html.Div]:
    indicators = _indicator_map(snapshot)
    symbols = [ind.symbol for ind in snapshot.indicators if ind.symbol not in ("10Y", "10Y-2Y")]
    tiles = []
    for symbol in symbols:
        indicator = indicators.get(symbol)
        if indicator is None:
            continue
        if indicator.latest_value is None:
            delta = "No price data"
            tone = "neutral_state"
        elif indicator.change_1d is not None and indicator.change_1m is not None:
            delta = f"1D {indicator.change_1d:+.1%} | 1M {indicator.change_1m:+.1%}"
            tone = "positive" if indicator.change_1d >= 0 else "negative"
        elif indicator.change_1d is not None:
            delta = f"1D {indicator.change_1d:+.1%}"
            tone = "positive" if indicator.change_1d >= 0 else "negative"
        else:
            delta = "Insufficient history"
            tone = "neutral_state"
        price = f"{indicator.latest_value:,.2f}" if indicator.latest_value is not None else "Unavailable"
        src_note = "via Yahoo Finance" if getattr(indicator, "source", None) == "yfinance" else None
        tiles.append(benchmark_card(symbol, price, delta, tone, source_note=src_note))
    return tiles


def _change_items(snapshot: RegimeOverviewSnapshot) -> list[html.Div]:
    indicators = _indicator_map(snapshot)
    notable = []
    for symbol in ["SPY", "BTC-USD", "USO", "DBC", "10Y", "10Y-2Y"]:
        indicator = indicators.get(symbol)
        if indicator is None:
            continue
        label = "1D" if indicator.change_1d is not None else "5D"
        change = indicator.change_1d if indicator.change_1d is not None else indicator.change_5d
        if change is None:
            continue
        notable.append((symbol, label, change))
    notable = sorted(notable, key=lambda item: abs(item[2]), reverse=True)[:4]
    return [
        html.Div(
            className="action-item",
            children=f"{symbol} {label} {change:+.1%}",
        )
        for symbol, label, change in notable
    ]


def render_regime_overview(snapshot: RegimeOverviewSnapshot, errors: list[str]):
    regime = snapshot.regime
    regime_transition = next((transition for transition in snapshot.transitions if transition.label == "Regime"), None)
    kpis = [
        MetricCard("Current Regime", regime.regime.title(), f"Strength {regime.regime_strength:.2f}", tone="market", icon="◫", emphasis="high"),
        MetricCard("Last Regime Flip", regime_transition.current_state.title() if regime_transition else regime.regime.title(), regime_transition.caption if regime_transition else "No transition history", tone="positive", icon="↺"),
        MetricCard("Growth", regime.growth_direction.title(), f"Score {next((point.growth_score for point in snapshot.regime_history[-1:]), 0.0):+.2f}", tone="positive" if regime.growth_direction == "up" else "negative", icon="↑"),
        MetricCard("Inflation", regime.inflation_direction.title(), f"Score {next((point.inflation_score for point in snapshot.regime_history[-1:]), 0.0):+.2f}", tone="warning" if regime.inflation_direction == "up" else "positive", icon="↕"),
    ]

    growth_score = snapshot.regime_history[-1].growth_score if snapshot.regime_history else 0.0
    inflation_score = snapshot.regime_history[-1].inflation_score if snapshot.regime_history else 0.0

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
                    html.Div(confirmation.last_transition.caption if confirmation.last_transition else "No transition history", className="terminal-caption"),
                ],
            )
        )

    growth_heat = heatstrip(
        [regime.component_scores.get("equity_trend"), regime.component_scores.get("cyclical_defensive_ratio"), regime.component_scores.get("copper_gold_ratio")],
        ["EQUITY", "CYCLICAL", "COPPER/GOLD"],
    )
    inflation_heat = heatstrip(
        [regime.component_scores.get("oil_trend"), regime.component_scores.get("commodity_trend"), regime.component_scores.get("yield_trend")],
        ["OIL", "COMMODITY", "10Y YIELD"],
    )

    return app_shell(
        [
            error_box(errors),
            html.Div(className="four-col", children=[metric_card(card) for card in kpis]),
            html.Div(
                className="hero-grid",
                children=[
                    section_panel(
                        "Regime Quadrant",
                        [
                            macro_quadrant(regime.regime, growth_score, inflation_score, regime.hybrid_label),
                            html.Div(className="chip-row", children=[badge(regime.growth_direction.upper(), "positive"), badge(regime.inflation_direction.upper(), "rates"), stat_chip("Market Tone", regime.regime.title(), "market")]),
                        ],
                        subtitle="Current macro environment",
                    ),
                    section_panel(
                        "What Changed",
                        [
                            transition_strip(snapshot.transitions),
                            html.Div(className="action-list", children=_change_items(snapshot)),
                        ],
                        subtitle="Historical transitions and recent moves",
                    ),
                ],
            ),
            section_panel("Indicator Tape", [html.Div(className="chart-wall", children=_benchmark_tiles(snapshot))], subtitle="Key KISS market indicators"),
            section_panel("Confirmation", [html.Div(className="signal-grid", children=confirmation_cards)], subtitle="VAMS used as confirmation, not sizing"),
            html.Div(
                className="two-col",
                children=[
                    section_panel("Growth Drivers", [growth_heat], subtitle="Regime inputs"),
                    section_panel("Inflation Drivers", [inflation_heat], subtitle="Regime inputs"),
                ],
            ),
        ],
        page_title="Regime, drivers, transitions, and confirming assets.",
        active_page="regime",
        status_meta={"as_of": snapshot.as_of, "scope": regime.regime.title()},
    )
