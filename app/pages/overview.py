from __future__ import annotations

import dash_mantine_components as dmc
from dash import dcc, html

from app.components.ui import (
    app_shell,
    badge,
    benchmark_card,
    macro_quadrant,
    metric_card,
    section_panel,
    signal_meter,
    stat_chip,
    transition_strip,
)
from app.config import AppConfig
from app.models import IndicatorSnapshot, MetricCard, RegimeOverviewSnapshot


def _indicator_map(snapshot: RegimeOverviewSnapshot) -> dict[str, IndicatorSnapshot]:
    return {indicator.symbol: indicator for indicator in snapshot.indicators}


def _benchmark_tiles(snapshot: RegimeOverviewSnapshot) -> list:
    indicators = _indicator_map(snapshot)
    symbols = [ind.symbol for ind in snapshot.indicators if ind.symbol not in ("10Y", "10Y-5Y")]
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


def _mover_chips(snapshot: RegimeOverviewSnapshot) -> list:
    indicators = _indicator_map(snapshot)
    notable = []
    for symbol in ["SPY", "BTC-USD", "USO", "DBC", "10Y", "10Y-5Y"]:
        indicator = indicators.get(symbol)
        if indicator is None:
            continue
        label = "1D" if indicator.change_1d is not None else "5D"
        change = indicator.change_1d if indicator.change_1d is not None else indicator.change_5d
        if change is None:
            continue
        notable.append((symbol, label, change))
    notable = sorted(notable, key=lambda item: abs(item[2]), reverse=True)[:6]
    return [
        badge(f"{symbol} {label} {change:+.1%}", "market" if change >= 0 else "negative")
        for symbol, label, change in notable
    ]
def render_regime_overview(snapshot: RegimeOverviewSnapshot, errors: list[str], config: AppConfig):
    regime = snapshot.regime
    regime_transition = next((transition for transition in snapshot.transitions if transition.label == "Regime"), None)
    weak_thr = float(config.regime_inputs.get("weak_score_threshold", 0.10))
    vol_hi = float(config.alert_thresholds.get("volatility_high_threshold", 0.35))
    benchmark_tiles = _benchmark_tiles(snapshot)

    kpis = [
        MetricCard("Current Regime", regime.regime.title(), f"Strength {regime.regime_strength:.2f}", tone="market", icon="◫", emphasis="high"),
        MetricCard(
            "Last Regime Flip",
            regime_transition.current_state.title() if regime_transition else regime.regime.title(),
            regime_transition.caption if regime_transition else "No transition history",
            tone="positive",
            icon="↺",
        ),
        MetricCard(
            "Growth",
            regime.growth_direction.title(),
            f"Score {snapshot.regime_history[-1].growth_score:+.2f}" if snapshot.regime_history else "—",
            tone="positive" if regime.growth_direction == "up" else "negative",
            icon="↑",
        ),
        MetricCard(
            "Inflation",
            regime.inflation_direction.title(),
            f"Score {snapshot.regime_history[-1].inflation_score:+.2f}" if snapshot.regime_history else "—",
            tone="warning" if regime.inflation_direction == "up" else "positive",
            icon="↕",
        ),
    ]

    growth_score = snapshot.regime_history[-1].growth_score if snapshot.regime_history else 0.0
    inflation_score = snapshot.regime_history[-1].inflation_score if snapshot.regime_history else 0.0
    strength_pct = min(100.0, max(0.0, regime.regime_strength * 100.0))
    hero = html.Div(
        className="summary-hero overview-hero",
        children=[
            html.Div(
                className="hero-split hero-main",
                children=[
                    html.Div(
                        className="hero-summary",
                        children=[
                            html.Div(
                                className="hero-regime-row",
                                children=[
                                    html.H2(regime.regime.title(), className="hero-regime"),
                                    badge(regime.hybrid_label, "warning") if regime.hybrid_label else badge("Confirmed", "positive"),
                                    badge(f"Growth {regime.growth_direction.upper()}", "positive" if regime.growth_direction == "up" else "negative"),
                                    badge(f"Inflation {regime.inflation_direction.upper()}", "warning" if regime.inflation_direction == "up" else "positive"),
                                ],
                            ),
                            html.Div(snapshot.summary_text or "Composite scores use a −1…+1 proxy scale per methodology.", className="hero-copy"),
                            html.Div(
                                className="hero-detail-row",
                                children=[
                                    stat
                                    for stat in [
                                        dmc.Tooltip(
                                            label=f"Growth composite (−1 bearish … +1 bullish). Weak if |score| < {weak_thr:.2f}.",
                                            children=stat_chip("Growth Score", f"{growth_score:+.2f}", "positive" if growth_score >= 0 else "negative"),
                                        ),
                                        dmc.Tooltip(
                                            label=f"Inflation composite (−1 … +1). Weak if |score| < {weak_thr:.2f}.",
                                            children=stat_chip("Inflation Score", f"{inflation_score:+.2f}", "warning" if inflation_score >= 0 else "positive"),
                                        ),
                                        stat_chip("Confirmations", str(len(snapshot.confirmations)), "market"),
                                        stat_chip("Weak Threshold", f"{weak_thr:.2f}", "neutral"),
                                    ]
                                ],
                            ),
                            html.Div(
                                f"Last flip: {regime_transition.caption}" if regime_transition else "No recent regime transition recorded.",
                                className="hero-support-text",
                            ),
                        ],
                    ),
                    html.Div(
                        className="hero-gauge tone-market",
                        children=[
                            html.Div("Regime Strength", className="hero-gauge-label"),
                            html.Div(f"{regime.regime_strength:.2f}", className="hero-gauge-value"),
                            html.Div(className="hero-band", children=[html.Div(className="hero-band-fill", style={"width": f"{strength_pct:.1f}%"})]),
                            html.Div(
                                f"Mean absolute growth/inflation score. Volatility alert threshold {vol_hi:.0%}.",
                                className="hero-gauge-caption",
                            ),
                        ],
                    ),
                ],
            ),
        ],
    )

    confirmation_cards = []
    for confirmation in snapshot.confirmations:
        confirmation_cards.append(
            dmc.Paper(
                children=[
                    dmc.Group(
                        [
                            dcc.Link(dmc.Text(confirmation.symbol, fw=700, c="cyan"), href=f"/ticker/{confirmation.symbol}", style={"textDecoration": "none"}),
                            badge(confirmation.state.upper(), confirmation.state),
                        ],
                        justify="space-between",
                    ),
                    dmc.Text(confirmation.role_label, size="xs", c="dimmed"),
                    signal_meter(confirmation.score, -1.0, 1.0, "Score", "market" if confirmation.score >= 0 else "negative"),
                    signal_meter(confirmation.trend or 0.0, -1.0, 1.0, "Trend", "market" if (confirmation.trend or 0.0) >= 0 else "negative"),
                    signal_meter(confirmation.momentum or 0.0, -1.0, 1.0, "Momentum", "market" if (confirmation.momentum or 0.0) >= 0 else "negative"),
                    signal_meter(confirmation.volatility or 0.0, 0.0, 1.0, "Volatility", "warning", threshold_mark=vol_hi, threshold_label=f"High vol {vol_hi:.0%}"),
                    dmc.Text(confirmation.last_transition.caption if confirmation.last_transition else "No transition history", size="xs", c="dimmed"),
                ],
                p="md",
                radius="lg",
                withBorder=True,
                className=f"sleeve-card tone-{confirmation.state if confirmation.state != 'neutral' else 'neutral_state'}",
            )
        )

    return app_shell(
        [
            hero,
            html.Div(className="kpi-rail kpi-strip", children=[metric_card(card) for card in kpis]),
            html.Div(
                className="section-row section-row-primary hero-grid",
                children=[
                    section_panel(
                        "Regime Quadrant",
                        [
                            macro_quadrant(regime.regime, growth_score, inflation_score, regime.hybrid_label),
                            html.Div(
                                className="chip-row",
                                children=[
                                    badge(regime.growth_direction.upper(), "positive"),
                                    badge(regime.inflation_direction.upper(), "rates"),
                                    dmc.Tooltip(label="Current classified regime label", children=badge(regime.regime.title(), "market")),
                                ],
                            ),
                        ],
                        subtitle="Current macro environment",
                        header_right=badge(regime.regime.title(), "market"),
                        density="compact",
                    ),
                    section_panel(
                        "What Changed",
                        [
                            transition_strip(snapshot.transitions),
                            html.Div(className="mover-chip-row", children=_mover_chips(snapshot)),
                        ],
                        subtitle="Regime / confirmation transitions and top absolute 1D or 5D moves",
                        header_right=badge(f"{len(snapshot.transitions)} events", "warning" if snapshot.transitions else "neutral"),
                        density="compact",
                    ),
                ],
            ),
            html.Div(
                className="section-row section-row-support",
                children=[
                    section_panel(
                        "Indicator Tape",
                        [html.Div(className="dense-card-grid benchmark-grid", children=benchmark_tiles or [html.Div("No indicator tape available.", className="empty-state")])],
                        subtitle="Key KISS market indicators",
                        header_right=badge(f"{len(benchmark_tiles)} tracked", "market"),
                        density="compact",
                    ),
                    section_panel(
                        "Confirmation",
                        [html.Div(className="dense-card-grid signal-grid", children=confirmation_cards or [html.Div("No confirmation assets available.", className="empty-state")])],
                        subtitle="VAMS used as confirmation, not sizing",
                        header_right=badge(f"{len(snapshot.confirmations)} sleeves", "positive" if snapshot.confirmations else "neutral"),
                        density="compact",
                    ),
                ],
            ),
        ],
        page_title="Regime, drivers, transitions, and confirming assets.",
        active_page="overview",
        status_meta={"as_of": snapshot.as_of, "scope": regime.regime.title()},
        warnings=errors,
    )
