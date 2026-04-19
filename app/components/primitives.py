"""HTML + Mantine building blocks for pages."""

from __future__ import annotations

from datetime import datetime
from typing import Callable, Iterable, Literal, Sequence

import dash_mantine_components as dmc
import pandas as pd
from dash import dcc, html

from app.components.charts import sparkline_chart
from app.components.theme import SLEEVE_COLORS
from app.models import AlertFlag, MetricCard, SignalChange, SignalTransition, SleeveAllocation, VamsSignal


def _format_timestamp(value: object) -> str:
    if value is None:
        return "Unavailable"
    if isinstance(value, pd.Timestamp):
        value = value.to_pydatetime()
    if isinstance(value, datetime):
        return value.strftime("%b %d, %Y")
    return str(value)


def _sleeve_color(symbol: str) -> str:
    return SLEEVE_COLORS.get(symbol.upper(), "#5bc0ff")


def _format_delta(value: float | None) -> str:
    if value is None:
        return "—"
    arrow = "▲" if value > 0 else "▼" if value < 0 else "•"
    return f"{arrow} {abs(value):.1%}"


def _empty_state(message: str = "Data unavailable for this section.") -> html.Div:
    return html.Div(message, className="empty-state")


def normalize_status_meta(meta: dict | None) -> dict:
    """Ensure status strip always has sensible keys."""
    m = dict(meta or {})
    if "as_of" not in m:
        m["as_of"] = None
    if "source" not in m:
        m["source"] = "yfinance"
    if "scope" not in m:
        m["scope"] = "KISS"
    return m


def section_panel(title: str, children, subtitle: str | None = None, extra_class: str = "") -> dmc.Paper:
    header = dmc.Stack(
        [
            dmc.Group(
                [
                    dmc.Text(title, size="sm", fw=700, tt="uppercase", c="cyan.4", style={"letterSpacing": "0.12em"}),
                ],
                justify="space-between",
            ),
            dmc.Text(subtitle, size="xs", c="dimmed") if subtitle else None,
        ],
        gap=4,
    )
    body = html.Div(className="section-body", children=children)
    return dmc.Paper(
        children=[header, body],
        className=f"section panel {extra_class}".strip(),
        p="md",
        withBorder=True,
        radius="lg",
    )


def badge(text: str, tone: str = "neutral") -> dmc.Badge:
    mapped = "gray" if tone == "neutral" else tone
    color_map = {
        "positive": "green",
        "negative": "red",
        "warning": "orange",
        "market": "cyan",
        "rates": "orange",
        "bullish": "green",
        "bearish": "red",
        "neutral_state": "gray",
    }
    return dmc.Badge(text, color=color_map.get(mapped, "gray"), variant="light", size="sm", tt="uppercase")


def stat_chip(label: str, value: str, tone: str = "neutral") -> html.Div:
    mapped = "neutral_state" if tone == "neutral" else tone
    return html.Div(
        className=f"stat-chip tone-{mapped}",
        children=[html.Span(label, className="stat-chip-label"), html.Span(value, className="stat-chip-value")],
    )


def metric_card(card: MetricCard) -> dmc.Paper:
    sparkline = None
    if card.sparkline:
        sparkline = sparkline_chart(card.sparkline, semantic=card.tone)
    kids = [
        dmc.Group(
            [
                dmc.Text(card.label, size="xs", c="dimmed", tt="uppercase"),
                dmc.Text(card.icon or "", size="sm"),
            ],
            justify="space-between",
        ),
        dmc.Text(card.value, size="xl", fw=700),
    ]
    if card.delta:
        kids.append(dmc.Text(card.delta, size="xs", c="dimmed"))
    kids.append(sparkline or html.Div(className="metric-sparkline-placeholder"))
    return dmc.Paper(
        children=kids,
        p="md",
        radius="lg",
        withBorder=True,
        className=f"metric-card metric-{card.variant} emphasis-{card.emphasis}",
    )


def benchmark_card(symbol: str, price: str, delta: str, tone: str, source_note: str | None = None) -> dmc.Paper:
    color = _sleeve_color(symbol)
    children: list = [
        dmc.Group(
            [
                html.Div(style={"width": 10, "height": 10, "borderRadius": 999, "backgroundColor": color}),
                dmc.Text(symbol, size="sm", fw=700, tt="uppercase"),
            ],
            gap="xs",
        ),
        dmc.Text(price, size="xl", fw=700),
        dmc.Text(delta, size="xs", c="dimmed"),
    ]
    if source_note:
        children.append(dmc.Text(source_note, size="xs", c="dimmed"))
    return dmc.Paper(children=children, p="sm", radius="lg", withBorder=True, className="benchmark-tile")


def error_box(errors: list[str]) -> html.Div | None:
    if not errors:
        return None
    return html.Div(
        className="warning-rack",
        children=[html.Div("Warnings", className="warning-title")] + [html.Div(error, className="warning-item") for error in errors],
    )


def warning_alerts(errors: list[str]) -> list:
    """Return Mantine Alert components for non-fatal warnings."""
    if not errors:
        return []
    return [dmc.Alert(title="Warning", color="yellow", children=e, mb="sm") for e in errors]


def signal_meter(
    value: float | None,
    min_value: float,
    max_value: float,
    label: str,
    semantic: str = "market",
    *,
    threshold_mark: float | None = None,
    threshold_label: str | None = None,
) -> html.Div:
    if value is None:
        value = 0.0
    span = max_value - min_value or 1.0
    position = ((value - min_value) / span) * 100
    position = max(0.0, min(position, 100.0))
    thumb_class = f"signal-meter-thumb tone-{semantic if semantic != 'neutral' else 'neutral_state'}"
    extra = []
    if threshold_mark is not None:
        tpos = ((threshold_mark - min_value) / span) * 100
        tpos = max(0.0, min(tpos, 100.0))
        extra.append(
            html.Div(
                title=threshold_label or "",
                style={
                    "position": "absolute",
                    "left": f"{tpos:.1f}%",
                    "top": "-2px",
                    "width": "3px",
                    "height": "12px",
                    "backgroundColor": "#ffb347",
                    "transform": "translateX(-50%)",
                },
            )
        )
    return html.Div(
        className="signal-meter",
        children=[
            html.Div(className="signal-meter-head", children=[html.Span(label), html.Span(f"{value:+.2f}")]),
            html.Div(
                className="signal-meter-track",
                children=[html.Div(className=thumb_class, style={"left": f"{position:.1f}%"})] + extra,
            ),
        ],
    )


def macro_quadrant(regime: str, growth_score: float, inflation_score: float, hybrid_label: str | None) -> html.Div:
    cells = [
        ("goldilocks", "GOLDILOCKS", "↑ Growth / ↓ Inflation"),
        ("reflation", "REFLATION", "↑ Growth / ↑ Inflation"),
        ("inflation", "INFLATION", "↓ Growth / ↑ Inflation"),
        ("deflation", "DEFLATION", "↓ Growth / ↓ Inflation"),
    ]
    point_left = max(0.0, min((growth_score + 1.0) / 2.0, 1.0)) * 100
    point_top = max(0.0, min((1.0 - ((inflation_score + 1.0) / 2.0)), 1.0)) * 100
    return html.Div(
        className="macro-quadrant",
        children=[
            html.Div(className="quadrant-label x-axis-pos", children="Growth +"),
            html.Div(className="quadrant-label x-axis-neg", children="Growth -"),
            html.Div(className="quadrant-label y-axis-pos", children="Inflation +"),
            html.Div(className="quadrant-label y-axis-neg", children="Inflation -"),
            html.Div(
                className="quadrant-grid",
                children=[
                    html.Div(
                        className=f"quadrant-cell {'is-active' if key == regime else ''}",
                        children=[html.Div(label, className="quadrant-cell-label"), html.Div(text, className="quadrant-cell-text")],
                    )
                    for key, label, text in cells
                ],
            ),
            html.Div(
                className="quadrant-point quadrant-point-pulse",
                style={"left": f"calc({point_left:.1f}% - 8px)", "top": f"calc({point_top:.1f}% - 8px)"},
                title=f"Growth: {growth_score:+.2f}, Inflation: {inflation_score:+.2f} (−1…+1 scale)",
            ),
            html.Div(
                className="quadrant-summary",
                children=[
                    badge(regime.title(), "market"),
                    badge(hybrid_label or "CONFIRMED", "warning" if hybrid_label else "positive"),
                ],
            ),
        ],
    )


def allocation_band(base: list[float], target: list[float], actual: list[float], labels: list[str], colors: dict[str, str] | None = None) -> html.Div:
    colors = colors or {}
    rows = [("Base", base), ("Target", target), ("Actual", actual)]
    legend = [
        html.Div(className="legend-item", children=[html.Div(className="legend-dot", style={"backgroundColor": colors.get(label, _sleeve_color(label))}), html.Span(label)])
        for label in labels
    ]
    return html.Div(
        className="allocation-band",
        children=[
            html.Div(className="allocation-legend", children=legend),
            html.Div(className="allocation-rows", children=[_allocation_row(name, values, labels, colors) for name, values in rows]),
        ],
    )


def _allocation_row(name: str, values: list[float], labels: list[str], colors: dict[str, str]) -> html.Div:
    total = sum(max(value, 0.0) for value in values) or 1.0
    segments = []
    for label, value in zip(labels, values):
        pct = max(value, 0.0) / total * 100
        segments.append(
            html.Div(
                className="allocation-segment",
                style={"width": f"{pct:.2f}%", "backgroundColor": colors.get(label, _sleeve_color(label))},
                title=f"{label} {value:.0%}",
            )
        )
    return html.Div(
        className="allocation-row",
        children=[
            html.Div(name, className="allocation-row-label"),
            html.Div(className="allocation-track", children=segments),
            html.Div(" ".join(f"{label} {value:.0%}" for label, value in zip(labels, values)), className="allocation-row-values"),
        ],
    )


def sleeve_state_card(allocation: SleeveAllocation, signal: VamsSignal | None = None) -> html.Div:
    sparkline = [allocation.base_weight, allocation.target_weight, allocation.actual_weight]
    tone = signal.state if signal else allocation.vams_state
    gap = allocation.target_weight - allocation.actual_weight
    signal = signal or VamsSignal(allocation.symbol, allocation.vams_state, 0.0, None, None, None, None, [])
    return html.Div(
        className=f"sleeve-card tone-{tone if tone != 'neutral' else 'neutral_state'}",
        children=[
            html.Div(
                className="sleeve-head",
                children=[
                    html.Div(
                        className="sleeve-head-left",
                        children=[
                            html.Div(className="symbol-dot", style={"backgroundColor": _sleeve_color(allocation.symbol)}),
                            html.Div(allocation.symbol, className="sleeve-symbol"),
                        ],
                    ),
                    badge(signal.state.upper(), tone),
                ],
            ),
            html.Div(
                className="sleeve-main-value",
                children=[html.Span(f"{allocation.actual_weight:.0%}", className="sleeve-actual"), html.Span(f"target {allocation.target_weight:.0%}", className="sleeve-target")],
            ),
            sparkline_chart(sparkline, semantic="market"),
            html.Div(
                className="sleeve-bars",
                children=[
                    signal_meter(allocation.base_weight, 0, 1, "Base", "neutral"),
                    signal_meter(allocation.target_weight, 0, 1, "Target", "market"),
                    signal_meter(allocation.actual_weight, 0, 1, "Actual", tone if tone != "neutral" else "neutral_state"),
                ],
            ),
            html.Div(
                className="sleeve-footer",
                children=[
                    stat_chip("Delta", _format_delta(allocation.delta_from_prior), "warning" if allocation.delta_from_prior else "neutral"),
                    stat_chip("Gap", f"{gap:+.1%}", "positive" if gap <= 0 else "warning"),
                ],
            ),
        ],
    )


def delta_strip(changes: list[SignalChange]) -> html.Div:
    if not changes:
        return html.Div(className="delta-strip empty", children=[html.Div("No changes in the current session.", className="terminal-caption")])
    items = []
    for change in changes[:6]:
        tone = "market"
        if "cash" in change.field:
            tone = "warning"
        elif "regime" in change.field:
            tone = "positive"
        items.append(
            html.Div(
                className=f"delta-event tone-{tone}",
                children=[
                    html.Div(change.symbol, className="delta-symbol"),
                    html.Div(change.field.replace("_", " ").title(), className="delta-field"),
                    html.Div(f"{change.old_value} -> {change.new_value}", className="delta-transition"),
                ],
            )
        )
    return html.Div(className="delta-strip", children=items)


def transition_strip(changes: list[SignalTransition]) -> html.Div:
    if not changes:
        return html.Div(className="delta-strip empty", children=[html.Div("No historical transition available.", className="terminal-caption")])
    items = []
    for change in changes[:6]:
        tone = "market"
        if "Regime" in change.label:
            tone = "positive"
        elif "BTC" in change.label:
            tone = "warning"
        items.append(
            html.Div(
                className=f"delta-event tone-{tone}",
                children=[
                    html.Div(change.label, className="delta-symbol"),
                    html.Div(change.current_state.upper(), className="delta-field"),
                    html.Div(change.caption, className="delta-transition"),
                ],
            )
        )
    return html.Div(className="delta-strip", children=items)


def heatstrip(
    values: Sequence[float | None],
    labels: Sequence[str],
    semantic_map: dict[str, str] | None = None,
    value_format: Literal["float", "percent", "yield"] = "float",
) -> html.Div:
    semantic_map = semantic_map or {}
    cells = []
    for label, value in zip(labels, values):
        if value is None:
            tone = "neutral_state"
            text = "—"
        else:
            tone = semantic_map.get(label, "market" if value >= 0 else "negative")
            if value_format == "percent":
                text = f"{value:+.1%}"
            elif value_format == "yield":
                text = f"{value:+.2%}"
            else:
                text = f"{value:+.2f}"
        cells.append(
            html.Div(
                className=f"heat-cell tone-{tone if tone != 'neutral' else 'neutral_state'}",
                children=[html.Div(label, className="heat-label"), html.Div(text, className="heat-value")],
            )
        )
    return html.Div(className="heatstrip", children=cells)


def alert_list(flags: Iterable[AlertFlag], title: str = "Alerts") -> dmc.Paper:
    rendered = [
        dmc.Group(
            [
                badge(flag.severity.upper(), "warning" if flag.severity == "medium" else "negative" if flag.severity == "high" else "neutral"),
                dmc.Text(flag.message, size="sm", c="dimmed"),
            ],
            align="flex-start",
            gap="sm",
        )
        for flag in flags
    ]
    if not rendered:
        return section_panel(title, [_empty_state("No active alerts")], extra_class="alerts-panel")
    return section_panel(title, rendered, extra_class="alerts-panel")


def insight_list(items: list[str], title: str) -> html.Div:
    pills = [html.Div(item, className="insight-pill") for item in items]
    return section_panel(title, pills, extra_class="insight-panel")


def feed_panel(title: str, frame: pd.DataFrame, title_column: str, secondary_columns: list[str]) -> dmc.Paper:
    if frame.empty or title_column not in frame.columns:
        return section_panel(title, [_empty_state()], extra_class="feed-panel")
    items = []
    for row in frame.head(6).to_dict("records"):
        secondary = " • ".join(
            str(row.get(column, "—"))
            for column in secondary_columns
            if row.get(column) not in {None, "", pd.NaT}
        )
        items.append(
            dmc.Paper(
                children=[
                    dmc.Text(str(row.get(title_column, "Untitled")), size="sm", fw=700),
                    dmc.Text(secondary or "No additional metadata", size="xs", c="dimmed"),
                ],
                p="sm",
                radius="md",
                withBorder=True,
            )
        )
    return section_panel(title, items, extra_class="feed-panel")


format_timestamp = _format_timestamp
