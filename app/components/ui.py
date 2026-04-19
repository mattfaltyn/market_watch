from __future__ import annotations

from datetime import datetime
from typing import Callable, Iterable, Literal, Sequence

import dash
from dash import dash_table, dcc, html
import pandas as pd
import plotly.graph_objects as go

from app.models import AlertFlag, MetricCard, SignalChange, SignalTransition, SleeveAllocation, VamsSignal


COLOR_MAP = {
    "positive": "#33d17a",
    "negative": "#ff6b6b",
    "warning": "#ffb347",
    "neutral": "#8aa4bf",
    "market": "#5bc0ff",
    "rates": "#ffb347",
    "bullish": "#33d17a",
    "neutral_state": "#8aa4bf",
    "bearish": "#ff6b6b",
}

SLEEVE_COLORS = {
    "SPY": "#4fb3ff",
    "AGG": "#8e8cf9",
    "BTC-USD": "#ff9f43",
    "USFR": "#39d98a",
    "QQQ": "#52d6ff",
    "IWM": "#c084fc",
    "DIA": "#f7c56b",
    "GLD": "#ffd166",
    "USO": "#ff7f50",
    "DBC": "#58d68d",
}


def _format_timestamp(value: object) -> str:
    if value is None:
        return "Unavailable"
    if isinstance(value, pd.Timestamp):
        value = value.to_pydatetime()
    if isinstance(value, datetime):
        return value.strftime("%b %d, %Y")
    return str(value)


def _series_color(semantic: str) -> str:
    return COLOR_MAP.get(semantic, COLOR_MAP["neutral"])


def _sleeve_color(symbol: str) -> str:
    return SLEEVE_COLORS.get(symbol.upper(), "#5bc0ff")


def _format_delta(value: float | None) -> str:
    if value is None:
        return "—"
    arrow = "▲" if value > 0 else "▼" if value < 0 else "•"
    return f"{arrow} {abs(value):.1%}"


def _empty_state(message: str = "Data unavailable for this section.") -> html.Div:
    return html.Div(message, className="empty-state")


def app_shell(
    children,
    page_title: str,
    active_page: str = "regime",
    status_meta: dict | None = None,
) -> html.Div:
    status_meta = status_meta or {}
    nav = [
        ("Regime", "/", "regime"),
        ("Signals", "/signals", "signals"),
        ("Market Watch", "/market-watch", "market-watch"),
    ]
    return html.Div(
        className="app-shell",
        children=[
            html.Div(
                className="app-frame",
                children=[
                    html.Div(
                        className="utility-row",
                        children=[
                            html.Div(
                                className="brand-block",
                                children=[
                                    html.Div("KISS / MARKET REGIME", className="brand-kicker"),
                                    html.H1("KISS Terminal"),
                                    html.P(page_title, className="subtitle"),
                                ],
                            ),
                            html.Div(
                                className="utility-actions",
                                children=[
                                    html.Div(
                                        className="status-strip",
                                        children=[
                                            _status_item("Source", str(status_meta.get("source", "yfinance"))),
                                            _status_item("As of", _format_timestamp(status_meta.get("as_of"))),
                                            _status_item("Scope", str(status_meta.get("scope", "KISS"))),
                                        ],
                                    ),
                                    html.Button("Refresh Data", id="refresh-button", n_clicks=0, className="refresh-button"),
                                ],
                            ),
                        ],
                    ),
                    html.Div(
                        className="nav-row",
                        children=[
                            dcc.Link(label, href=href, className=f"nav-pill {'is-active' if active_page == key else ''}")
                            for label, href, key in nav
                        ],
                    ),
                ],
            ),
            html.Div(className="page-body-wrap", children=[html.Div(className="page-body", children=children)]),
        ],
    )


def _status_item(label: str, value: str) -> html.Div:
    return html.Div(
        className="status-item",
        children=[html.Span(label, className="status-label"), html.Span(value, className="status-value")],
    )


def section_panel(title: str, children, subtitle: str | None = None, extra_class: str = "") -> html.Div:
    header_children = [html.H3(title, className="section-title")]
    if subtitle:
        header_children.append(html.Div(subtitle, className="section-subtitle"))
    return html.Div(
        className=f"section panel {extra_class}".strip(),
        children=[html.Div(className="section-header", children=header_children), html.Div(className="section-body", children=children)],
    )


def badge(text: str, tone: str = "neutral") -> html.Span:
    mapped = "neutral_state" if tone == "neutral" else tone
    return html.Span(text, className=f"badge tone-{mapped}")


def stat_chip(label: str, value: str, tone: str = "neutral") -> html.Div:
    mapped = "neutral_state" if tone == "neutral" else tone
    return html.Div(
        className=f"stat-chip tone-{mapped}",
        children=[html.Span(label, className="stat-chip-label"), html.Span(value, className="stat-chip-value")],
    )


def metric_card(card: MetricCard) -> html.Div:
    tone = "neutral_state" if card.tone == "neutral" else card.tone
    sparkline = None
    if card.sparkline:
        sparkline = sparkline_chart(card.sparkline, semantic=card.tone)
    return html.Div(
        className=f"metric-card metric-{card.variant} tone-{tone} emphasis-{card.emphasis}",
        children=[
            html.Div(
                className="metric-topline",
                children=[
                    html.Div(card.label, className="metric-label"),
                    html.Div(card.icon or "", className="metric-icon"),
                ],
            ),
            html.Div(card.value, className="metric-value"),
            html.Div(card.delta or "", className="metric-delta"),
            sparkline or html.Div(className="metric-sparkline-placeholder"),
        ],
    )


def benchmark_card(symbol: str, price: str, delta: str, tone: str, source_note: str | None = None) -> html.Div:
    color = _sleeve_color(symbol)
    mapped = "neutral_state" if tone == "neutral" else tone
    children: list = [
        html.Div(className="benchmark-head", children=[html.Div(className="symbol-dot", style={"backgroundColor": color}), html.Div(symbol, className="benchmark-symbol")]),
        html.Div(price, className="benchmark-price"),
        html.Div(delta, className="benchmark-returns"),
    ]
    if source_note:
        children.append(html.Div(source_note, className="benchmark-source-note"))
    return html.Div(
        className=f"benchmark-tile tone-{mapped}",
        children=children,
    )


def error_box(errors: list[str]) -> html.Div | None:
    if not errors:
        return None
    return html.Div(
        className="warning-rack",
        children=[html.Div("Warnings", className="warning-title")] + [html.Div(error, className="warning-item") for error in errors],
    )


def fatal_error_page(title: str, errors: list[str], guidance: list[str] | None = None) -> html.Div:
    guidance = guidance or []
    return app_shell(
        [
            section_panel(
                title,
                [
                    html.Div("The dashboard could not finish loading its data.", className="terminal-caption"),
                    error_box(errors) or _empty_state("Unknown error"),
                    html.Div(className="guidance-list", children=[html.Div(item, className="guidance-item") for item in guidance]),
                ],
                subtitle="Load error",
                extra_class="fatal-panel",
            )
        ],
        page_title="Dashboard load error",
        active_page="regime",
        status_meta={"scope": "Load failure"},
    )


def sparkline_chart(values: Sequence[float] | pd.Series, semantic: str = "market") -> dcc.Graph | html.Div:
    series = pd.Series(list(values), dtype=float).dropna()
    if series.empty:
        return _empty_state("Unavailable")
    figure = go.Figure(
        go.Scatter(
            x=list(range(len(series))),
            y=series,
            mode="lines",
            line={"color": _series_color(semantic), "width": 2},
            fill="tozeroy",
            fillcolor="rgba(91,192,255,0.10)" if semantic == "market" else "rgba(51,209,122,0.10)" if semantic == "positive" else "rgba(255,159,67,0.10)",
        )
    )
    figure.update_layout(
        margin={"l": 0, "r": 0, "t": 0, "b": 0},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=44,
        showlegend=False,
    )
    figure.update_xaxes(visible=False)
    figure.update_yaxes(visible=False)
    return dcc.Graph(figure=figure, config={"displayModeBar": False}, className="sparkline")


def make_pie_chart(labels: list[str], values: list[float], title: str) -> dcc.Graph | html.Div:
    if not labels or not values:
        return _empty_state()
    figure = go.Figure(
        data=[
            go.Pie(
                labels=labels,
                values=values,
                hole=0.68,
                marker={"colors": [_sleeve_color(label) for label in labels], "line": {"color": "#081521", "width": 2}},
                textinfo="percent",
                textfont={"color": "#e6f1ff", "size": 13},
            )
        ]
    )
    figure.update_layout(
        title={"text": title, "x": 0.03, "xanchor": "left", "font": {"color": "#e6f1ff", "size": 14}},
        margin={"l": 10, "r": 10, "t": 44, "b": 10},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=300,
        showlegend=False,
    )
    return dcc.Graph(figure=figure, config={"displayModeBar": False}, className="chart")


def make_line_chart(
    frame: pd.DataFrame,
    x: str,
    y_columns: list[str],
    title: str,
    semantic: str = "market",
    compact: bool = False,
) -> dcc.Graph | html.Div:
    usable = frame.copy()
    if usable.empty or x not in usable.columns or not any(column in usable.columns for column in y_columns):
        return _empty_state()
    figure = go.Figure()
    for index, column in enumerate(y_columns):
        if column in usable.columns:
            figure.add_trace(
                go.Scatter(
                    x=usable[x],
                    y=usable[column],
                    mode="lines",
                    name=column.replace("_", " ").title(),
                    line={"width": 2.5 if index == 0 else 1.6, "color": _series_color(semantic) if index == 0 else "#8aa4bf"},
                    fill="tozeroy" if len(y_columns) == 1 else None,
                    fillcolor="rgba(91,192,255,0.08)" if semantic == "market" and len(y_columns) == 1 else None,
                )
            )
    figure.update_layout(
        title={"text": title, "x": 0.03, "xanchor": "left", "font": {"color": "#e6f1ff", "size": 14}} if title else None,
        margin={"l": 10, "r": 10, "t": 42 if title else 8, "b": 20},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        template="plotly_dark",
        height=180 if compact else 280,
        showlegend=not compact and len(y_columns) > 1,
        hoverlabel={"bgcolor": "#0d1b29", "font_color": "#e6f1ff"},
    )
    figure.update_xaxes(showgrid=False, zeroline=False, color="#7f96ad")
    figure.update_yaxes(showgrid=True, gridcolor="rgba(140,163,186,0.14)", zeroline=False, color="#7f96ad")
    return dcc.Graph(figure=figure, config={"displayModeBar": False}, className="chart")


def make_bar_chart(frame: pd.DataFrame, x: str, title: str, semantic: str = "market") -> dcc.Graph | html.Div:
    if frame.empty or x not in frame.columns:
        return _empty_state()
    value_columns = [column for column in frame.columns if column not in {"symbol", "report_date", x}]
    if not value_columns:
        return _empty_state()
    latest = frame.sort_values(x).tail(1)
    melted = latest.melt(id_vars=[x], value_vars=value_columns, var_name="series", value_name="value")
    figure = go.Figure(
        go.Bar(
            x=melted["series"],
            y=melted["value"],
            marker_color=[_series_color(semantic)] * len(melted),
            marker_line={"color": "#081521", "width": 1.5},
        )
    )
    figure.update_layout(
        title={"text": title, "x": 0.03, "xanchor": "left", "font": {"color": "#e6f1ff", "size": 14}},
        margin={"l": 10, "r": 10, "t": 42, "b": 20},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        template="plotly_dark",
        height=260,
    )
    figure.update_xaxes(showgrid=False, color="#7f96ad")
    figure.update_yaxes(showgrid=True, gridcolor="rgba(140,163,186,0.14)", color="#7f96ad")
    return dcc.Graph(figure=figure, config={"displayModeBar": False}, className="chart")


def exposure_gauge(value: float | None, label: str, tone: str = "market") -> html.Div:
    if value is None:
        return section_panel(label, [_empty_state("Unavailable")], extra_class="gauge-panel")
    mapped = "neutral_state" if tone == "neutral" else tone
    figure = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=max(0.0, min(value * 100, 100.0)),
            number={"suffix": "%", "font": {"size": 28, "color": "#f5fbff"}},
            gauge={
                "shape": "angular",
                "axis": {"range": [0, 100], "tickcolor": "#54718f", "tickwidth": 1},
                "bar": {"color": _series_color(mapped)},
                "bgcolor": "rgba(18,32,46,0.65)",
                "borderwidth": 0,
                "steps": [
                    {"range": [0, 35], "color": "rgba(140,163,186,0.12)"},
                    {"range": [35, 70], "color": "rgba(140,163,186,0.20)"},
                    {"range": [70, 100], "color": "rgba(140,163,186,0.28)"},
                ],
            },
        )
    )
    figure.update_layout(
        margin={"l": 12, "r": 12, "t": 10, "b": 0},
        paper_bgcolor="rgba(0,0,0,0)",
        height=180,
    )
    return html.Div(className="terminal-gauge", children=[html.Div(label, className="mini-panel-label"), dcc.Graph(figure=figure, config={"displayModeBar": False})])


def signal_meter(value: float | None, min_value: float, max_value: float, label: str, semantic: str = "market") -> html.Div:
    if value is None:
        value = 0.0
    span = max_value - min_value or 1.0
    position = ((value - min_value) / span) * 100
    position = max(0.0, min(position, 100.0))
    return html.Div(
        className="signal-meter",
        children=[
            html.Div(className="signal-meter-head", children=[html.Span(label), html.Span(f"{value:+.2f}")]),
            html.Div(
                className="signal-meter-track",
                children=[html.Div(className=f"signal-meter-thumb tone-{semantic if semantic != 'neutral' else 'neutral_state'}", style={"left": f"{position:.1f}%"})],
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
                children=[html.Div(className=f"quadrant-cell {'is-active' if key == regime else ''}", children=[html.Div(label, className="quadrant-cell-label"), html.Div(text, className="quadrant-cell-text")]) for key, label, text in cells],
            ),
            html.Div(className="quadrant-point", style={"left": f"calc({point_left:.1f}% - 8px)", "top": f"calc({point_top:.1f}% - 8px)"}),
            html.Div(className="quadrant-summary", children=[badge(regime.title(), "market"), badge(hybrid_label or "CONFIRMED", "warning" if hybrid_label else "positive")]),
        ],
    )


def allocation_band(base: list[float], target: list[float], actual: list[float], labels: list[str], colors: dict[str, str] | None = None) -> html.Div:
    colors = colors or {}
    rows = [("Base", base), ("Target", target), ("Actual", actual)]
    legend = [html.Div(className="legend-item", children=[html.Div(className="legend-dot", style={"backgroundColor": colors.get(label, _sleeve_color(label))}), html.Span(label)]) for label in labels]
    return html.Div(
        className="allocation-band",
        children=[
            html.Div(className="allocation-legend", children=legend),
            html.Div(
                className="allocation-rows",
                children=[_allocation_row(name, values, labels, colors) for name, values in rows],
            ),
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
                    html.Div(className="sleeve-head-left", children=[html.Div(className="symbol-dot", style={"backgroundColor": _sleeve_color(allocation.symbol)}), html.Div(allocation.symbol, className="sleeve-symbol")]),
                    badge(signal.state.upper(), tone),
                ],
            ),
            html.Div(className="sleeve-main-value", children=[html.Span(f"{allocation.actual_weight:.0%}", className="sleeve-actual"), html.Span(f"target {allocation.target_weight:.0%}", className="sleeve-target")]),
            sparkline_chart(sparkline, semantic="market"),
            html.Div(className="sleeve-bars", children=[signal_meter(allocation.base_weight, 0, 1, "Base", "neutral"), signal_meter(allocation.target_weight, 0, 1, "Target", "market"), signal_meter(allocation.actual_weight, 0, 1, "Actual", tone if tone != "neutral" else "neutral_state")]),
            html.Div(className="sleeve-footer", children=[stat_chip("Delta", _format_delta(allocation.delta_from_prior), "warning" if allocation.delta_from_prior else "neutral"), stat_chip("Gap", f"{gap:+.1%}", "positive" if gap <= 0 else "warning")]),
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


def _format_numeric(value: object, column: str) -> object:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "—"
    if isinstance(value, pd.Timestamp):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float)):
        if "return" in column.lower() or "spread" in column.lower() or "margin" in column.lower() or "growth" in column.lower() or column.lower() in {"base", "target", "actual", "gap", "delta", "score", "trend", "momentum", "volatility"}:
            return f"{value:+.1%}" if abs(value) <= 1.5 else f"{value:.2f}"
        if "days_to" in column.lower() or "count" in column.lower() or "alert" in column.lower():
            return f"{value:.0f}"
        if abs(value) >= 1000:
            return f"{value:,.2f}"
        return f"{value:.2f}"
    return value


def make_table(
    frame: pd.DataFrame,
    link_column: str | None = None,
    column_formatters: dict[str, Callable[[object], object]] | None = None,
    numeric_columns: list[str] | None = None,
) -> dash_table.DataTable | html.Div:
    if frame.empty:
        return _empty_state()
    data = frame.copy()
    column_formatters = column_formatters or {}
    numeric_columns = numeric_columns or [column for column in data.columns if pd.api.types.is_numeric_dtype(data[column])]
    for column in data.columns:
        formatter = column_formatters.get(column)
        if formatter is not None:
            data[column] = data[column].map(formatter)
        else:
            data[column] = data[column].map(lambda value, c=column: _format_numeric(value, c))
    if link_column and link_column in data.columns:
        data[link_column] = data[link_column].astype(str)
    return dash_table.DataTable(
        data=data.to_dict("records"),
        columns=[{"name": column, "id": column} for column in data.columns],
        sort_action="native",
        page_size=12,
        style_table={"overflowX": "auto", "border": "1px solid rgba(127,150,173,0.16)", "borderRadius": "18px", "backgroundColor": "#0d1722"},
        style_cell={
            "textAlign": "left",
            "padding": "11px 12px",
            "fontFamily": "\"IBM Plex Sans\", \"Avenir Next\", sans-serif",
            "fontSize": 12,
            "backgroundColor": "rgba(13,23,34,0.95)",
            "color": "#d5e7f7",
            "border": "none",
            "borderBottom": "1px solid rgba(127,150,173,0.10)",
            "maxWidth": 220,
            "whiteSpace": "normal",
        },
        style_cell_conditional=[{"if": {"column_id": column}, "textAlign": "right"} for column in numeric_columns],
        style_data_conditional=[{"if": {"row_index": "odd"}, "backgroundColor": "rgba(17,31,44,0.92)"}],
        style_header={
            "fontWeight": 700,
            "backgroundColor": "#122231",
            "color": "#7f96ad",
            "textTransform": "uppercase",
            "fontSize": 10,
            "letterSpacing": "0.10em",
            "borderBottom": "1px solid rgba(127,150,173,0.20)",
        },
    )


def alert_list(flags: Iterable[AlertFlag], title: str = "Alerts") -> html.Div:
    rendered = [
        html.Div(
            className="alert-item",
            children=[
                badge(flag.severity.upper(), "warning" if flag.severity == "medium" else "negative" if flag.severity == "high" else "neutral"),
                html.Div(flag.message, className="alert-text"),
            ],
        )
        for flag in flags
    ]
    if not rendered:
        return section_panel(title, [_empty_state("No active alerts")], extra_class="alerts-panel")
    return section_panel(title, rendered, extra_class="alerts-panel")


def insight_list(items: list[str], title: str) -> html.Div:
    pills = [html.Div(item, className="insight-pill") for item in items]
    return section_panel(title, pills, extra_class="insight-panel")


def feed_panel(title: str, frame: pd.DataFrame, title_column: str, secondary_columns: list[str]) -> html.Div:
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
            html.Div(
                className="feed-item",
                children=[
                    html.Div(str(row.get(title_column, "Untitled")), className="feed-title"),
                    html.Div(secondary or "No additional metadata", className="feed-meta"),
                ],
            )
        )
    return section_panel(title, items, extra_class="feed-panel")


APP_CSS = """
:root {
  --bg: #07111a;
  --bg-glow: #0d1722;
  --surface: rgba(11, 22, 33, 0.96);
  --surface-soft: rgba(18, 34, 49, 0.96);
  --surface-lift: rgba(15, 27, 40, 0.98);
  --text: #e6f1ff;
  --text-muted: #91a7bd;
  --text-soft: #667b91;
  --border: rgba(127, 150, 173, 0.18);
  --border-strong: rgba(127, 150, 173, 0.28);
  --shadow: 0 24px 48px rgba(0, 0, 0, 0.38);
  --radius-xl: 26px;
  --radius-lg: 20px;
  --radius-md: 14px;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  font-family: "IBM Plex Sans", "Avenir Next", sans-serif;
  background:
    radial-gradient(circle at top left, rgba(41, 86, 121, 0.28) 0%, rgba(7, 17, 26, 0) 35%),
    radial-gradient(circle at top right, rgba(255, 159, 67, 0.14) 0%, rgba(7, 17, 26, 0) 28%),
    linear-gradient(180deg, var(--bg) 0%, #050d14 100%);
  color: var(--text);
}
a { color: #d5e7f7; text-decoration: none; font-weight: 600; }
.app-shell { min-height: 100vh; }
.app-frame {
  position: sticky; top: 0; z-index: 10; padding: 18px 22px 0;
  background: linear-gradient(180deg, rgba(7, 17, 26, 0.94) 0%, rgba(7, 17, 26, 0.64) 100%);
  backdrop-filter: blur(18px);
}
.utility-row, .nav-row {
  max-width: 1480px; margin: 0 auto; background: rgba(9, 18, 28, 0.88);
  border: 1px solid var(--border); box-shadow: var(--shadow);
}
.utility-row {
  padding: 18px 22px 16px; display: flex; gap: 18px; justify-content: space-between; align-items: center;
  border-radius: var(--radius-xl) var(--radius-xl) 0 0;
}
.brand-kicker {
  font-size: 10px; letter-spacing: 0.16em; text-transform: uppercase; color: #5bc0ff; margin-bottom: 6px;
}
.brand-block h1 { margin: 0; font-size: 46px; letter-spacing: -0.06em; }
.subtitle { margin: 6px 0 0; color: var(--text-muted); font-size: 15px; }
.utility-actions { display: flex; gap: 18px; align-items: center; }
.status-strip { display: flex; gap: 14px; flex-wrap: wrap; }
.status-item { display: flex; flex-direction: column; gap: 4px; padding-right: 14px; border-right: 1px solid rgba(127, 150, 173, 0.12); }
.status-item:last-child { border-right: none; }
.status-label { font-size: 10px; text-transform: uppercase; letter-spacing: 0.12em; color: var(--text-soft); }
.status-value { font-size: 13px; color: var(--text); font-weight: 600; }
.refresh-button {
  border: 1px solid rgba(91, 192, 255, 0.25); border-radius: 999px;
  background: linear-gradient(135deg, #0f2738 0%, #173a56 100%);
  color: white; padding: 12px 18px; font-weight: 700; cursor: pointer;
  box-shadow: 0 14px 28px rgba(0, 0, 0, 0.25);
}
.nav-row {
  padding: 12px 22px 16px; display: flex; gap: 10px;
  border-top: none; border-radius: 0 0 var(--radius-xl) var(--radius-xl);
}
.nav-pill {
  padding: 10px 16px; border-radius: 999px; color: var(--text-muted);
  background: rgba(18, 34, 49, 0.82); border: 1px solid rgba(127, 150, 173, 0.10);
}
.nav-pill.is-active { background: #5bc0ff; color: #03101b; }
.page-body-wrap { padding: 24px 22px 52px; }
.page-body { max-width: 1480px; margin: 0 auto; display: grid; gap: 18px; }
.hero-grid, .two-col, .info-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 18px; }
.three-col { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 18px; }
.four-col { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 14px; }
.kpi-strip { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 14px; }
.sleeve-grid, .signal-grid, .proxy-grid, .chart-wall { display: grid; grid-template-columns: repeat(auto-fit, minmax(230px, 1fr)); gap: 16px; }
.section.panel, .metric-card, .benchmark-tile, .sleeve-card, .terminal-gauge {
  background: linear-gradient(180deg, rgba(15, 27, 40, 0.96) 0%, rgba(9, 18, 28, 0.98) 100%);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow);
}
.section.panel { padding: 18px; }
.section-header { display: flex; justify-content: space-between; align-items: flex-start; gap: 10px; margin-bottom: 14px; }
.section-title { margin: 0; font-size: 14px; letter-spacing: 0.12em; text-transform: uppercase; color: #5bc0ff; }
.section-subtitle, .terminal-caption { color: var(--text-muted); font-size: 12px; }
.metric-card { padding: 16px; display: grid; gap: 10px; min-height: 156px; }
.metric-topline { display: flex; justify-content: space-between; align-items: center; gap: 8px; }
.metric-label { font-size: 11px; letter-spacing: 0.12em; text-transform: uppercase; color: var(--text-soft); }
.metric-icon { color: #5bc0ff; font-size: 14px; min-height: 14px; }
.metric-value { font-size: 30px; font-weight: 700; letter-spacing: -0.05em; }
.metric-delta { color: var(--text-muted); font-size: 12px; line-height: 1.4; min-height: 34px; }
.metric-compact .metric-value { font-size: 22px; }
.metric-compact { min-height: 132px; }
.metric-sparkline-placeholder { height: 44px; }
.warning-rack, .guidance-list { display: grid; gap: 8px; }
.warning-title { font-size: 11px; letter-spacing: 0.12em; text-transform: uppercase; color: #ffb347; }
.warning-item, .guidance-item { background: rgba(18,34,49,0.82); border: 1px solid rgba(255,179,71,0.16); border-radius: 12px; padding: 10px 12px; color: #ffd8a8; }
.badge {
  display: inline-flex; align-items: center; border-radius: 999px; padding: 6px 10px;
  font-size: 10px; font-weight: 700; letter-spacing: 0.10em; text-transform: uppercase;
  background: rgba(127, 150, 173, 0.16); color: #d5e7f7;
}
.stat-chip {
  display: grid; gap: 4px; padding: 10px 12px; border-radius: 12px;
  background: rgba(18, 34, 49, 0.8); border: 1px solid rgba(127, 150, 173, 0.14);
}
.stat-chip-label { font-size: 10px; letter-spacing: 0.10em; text-transform: uppercase; color: var(--text-soft); }
.stat-chip-value { font-size: 12px; color: var(--text); }
.tone-positive, .tone-bullish { border-color: rgba(51,209,122,0.35); }
.tone-negative, .tone-bearish { border-color: rgba(255,107,107,0.35); }
.tone-warning, .tone-rates { border-color: rgba(255,179,71,0.35); }
.tone-market { border-color: rgba(91,192,255,0.35); }
.tone-neutral_state { border-color: rgba(138,164,191,0.28); }
.benchmark-tile { padding: 14px; display: grid; gap: 8px; min-height: 116px; }
.benchmark-head, .sleeve-head, .sleeve-head-left { display: flex; align-items: center; gap: 8px; justify-content: space-between; }
.sleeve-head-left { justify-content: flex-start; }
.symbol-dot, .legend-dot { width: 10px; height: 10px; border-radius: 999px; }
.benchmark-symbol, .sleeve-symbol { font-size: 13px; font-weight: 700; letter-spacing: 0.10em; }
.benchmark-price { font-size: 26px; font-weight: 700; letter-spacing: -0.04em; }
.benchmark-returns { font-size: 12px; color: var(--text-muted); }
.benchmark-source-note { font-size: 10px; color: var(--text-muted); letter-spacing: 0.04em; }
.allocation-band { display: grid; gap: 14px; }
.allocation-legend { display: flex; gap: 12px; flex-wrap: wrap; }
.legend-item { display: flex; align-items: center; gap: 8px; color: var(--text-muted); font-size: 12px; }
.allocation-rows { display: grid; gap: 12px; }
.allocation-row { display: grid; grid-template-columns: 80px 1fr minmax(180px, 260px); gap: 12px; align-items: center; }
.allocation-row-label { font-size: 11px; letter-spacing: 0.12em; text-transform: uppercase; color: var(--text-soft); }
.allocation-track { display: flex; height: 18px; border-radius: 999px; overflow: hidden; background: rgba(127,150,173,0.10); border: 1px solid rgba(127,150,173,0.12); }
.allocation-segment { height: 100%; }
.allocation-row-values { font-size: 12px; color: var(--text-muted); text-align: right; }
.macro-quadrant { position: relative; min-height: 320px; }
.quadrant-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; }
.quadrant-cell {
  min-height: 128px; padding: 16px; border-radius: 18px; border: 1px solid rgba(127,150,173,0.16);
  background: rgba(18, 34, 49, 0.72); display: grid; align-content: end; gap: 8px;
}
.quadrant-cell.is-active { border-color: rgba(91,192,255,0.62); box-shadow: inset 0 0 0 1px rgba(91,192,255,0.34); }
.quadrant-cell-label { font-size: 16px; font-weight: 700; letter-spacing: 0.06em; }
.quadrant-cell-text { color: var(--text-muted); font-size: 12px; }
.quadrant-label { position: absolute; font-size: 10px; letter-spacing: 0.12em; text-transform: uppercase; color: var(--text-soft); }
.x-axis-pos { right: 18px; bottom: -4px; }
.x-axis-neg { left: 18px; bottom: -4px; }
.y-axis-pos { top: -6px; right: 22px; }
.y-axis-neg { bottom: 30px; left: -2px; transform: rotate(-90deg); transform-origin: left bottom; }
.quadrant-point {
  position: absolute; width: 16px; height: 16px; border-radius: 999px; background: #ff9f43; border: 2px solid #07111a;
  box-shadow: 0 0 0 4px rgba(255,159,67,0.22);
}
.quadrant-summary { margin-top: 16px; display: flex; gap: 8px; flex-wrap: wrap; }
.signal-meter { display: grid; gap: 6px; }
.signal-meter-head { display: flex; justify-content: space-between; color: var(--text-muted); font-size: 11px; }
.signal-meter-track { position: relative; height: 8px; border-radius: 999px; background: rgba(127,150,173,0.12); overflow: hidden; }
.signal-meter-thumb { position: absolute; top: 0; width: 16px; height: 8px; border-radius: 999px; transform: translateX(-50%); }
.signal-meter-thumb.tone-market { background: #5bc0ff; }
.signal-meter-thumb.tone-rates, .signal-meter-thumb.tone-warning { background: #ffb347; }
.signal-meter-thumb.tone-positive, .signal-meter-thumb.tone-bullish { background: #33d17a; }
.signal-meter-thumb.tone-negative, .signal-meter-thumb.tone-bearish { background: #ff6b6b; }
.signal-meter-thumb.tone-neutral_state { background: #8aa4bf; }
.terminal-gauge { padding: 14px; }
.mini-panel-label { font-size: 11px; letter-spacing: 0.12em; text-transform: uppercase; color: var(--text-soft); margin-bottom: 6px; }
.sleeve-card { padding: 16px; display: grid; gap: 12px; }
.sleeve-main-value { display: flex; align-items: baseline; justify-content: space-between; gap: 10px; }
.sleeve-actual { font-size: 30px; font-weight: 700; letter-spacing: -0.05em; }
.sleeve-target { color: var(--text-muted); font-size: 12px; }
.sleeve-bars, .sleeve-footer { display: grid; gap: 10px; }
.sleeve-footer { grid-template-columns: repeat(2, minmax(0, 1fr)); }
.delta-strip { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; }
.delta-event {
  padding: 12px; border-radius: 16px; background: rgba(18,34,49,0.82); border: 1px solid rgba(127,150,173,0.16); display: grid; gap: 6px;
}
.delta-symbol { font-size: 11px; letter-spacing: 0.12em; text-transform: uppercase; color: var(--text-soft); }
.delta-field { font-size: 14px; font-weight: 700; }
.delta-transition { font-size: 12px; color: var(--text-muted); }
.delta-strip.empty { padding: 14px; border-radius: 16px; background: rgba(18,34,49,0.72); border: 1px dashed rgba(127,150,173,0.16); }
.insight-panel .section-body { display: flex; flex-wrap: wrap; gap: 10px; }
.insight-pill {
  padding: 10px 12px; border-radius: 14px; background: rgba(18,34,49,0.82);
  border: 1px solid rgba(127,150,173,0.14); color: var(--text-muted); font-size: 12px;
}
.feed-panel .section-body, .alerts-panel .section-body { display: grid; gap: 10px; }
.feed-item, .alert-item {
  padding: 12px; border-radius: 14px; background: rgba(18,34,49,0.82); border: 1px solid rgba(127,150,173,0.14); display: grid; gap: 8px;
}
.feed-title { font-weight: 700; }
.feed-meta, .alert-text { color: var(--text-muted); font-size: 12px; }
.heatstrip { display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 10px; }
.heat-cell {
  padding: 10px 12px; border-radius: 14px; background: rgba(18,34,49,0.82); border: 1px solid rgba(127,150,173,0.14); display: grid; gap: 6px;
}
.heat-label { font-size: 10px; text-transform: uppercase; letter-spacing: 0.10em; color: var(--text-soft); }
.heat-value { font-size: 16px; font-weight: 700; }
.empty-state {
  padding: 16px; border-radius: 14px; background: rgba(18,34,49,0.72); border: 1px dashed rgba(127,150,173,0.16); color: var(--text-muted); font-size: 12px;
}
.sparkline .js-plotly-plot, .chart .js-plotly-plot { width: 100% !important; }
.ticker-header, .status-rail { display: grid; grid-template-columns: 1.4fr 1fr; gap: 18px; }
.ticker-company { font-size: 28px; font-weight: 700; letter-spacing: -0.04em; }
.ticker-symbol { font-size: 12px; letter-spacing: 0.16em; text-transform: uppercase; color: #5bc0ff; }
.meta-row, .chip-row, .action-list { display: flex; gap: 8px; flex-wrap: wrap; }
.terminal-title-row { display: flex; justify-content: space-between; align-items: center; gap: 12px; }
.section-metric-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }
.mini-stat {
  padding: 12px; border-radius: 14px; background: rgba(18,34,49,0.82); border: 1px solid rgba(127,150,173,0.14); display: grid; gap: 6px;
}
.mini-stat-label { font-size: 10px; text-transform: uppercase; letter-spacing: 0.10em; color: var(--text-soft); }
.mini-stat-value { font-size: 22px; font-weight: 700; }
.action-item {
  padding: 10px 12px; border-radius: 14px; background: rgba(18,34,49,0.82); border: 1px solid rgba(91,192,255,0.16); font-size: 12px;
}
@media (max-width: 1120px) {
  .hero-grid, .two-col, .three-col, .kpi-strip, .ticker-header, .status-rail { grid-template-columns: 1fr; }
  .allocation-row { grid-template-columns: 1fr; }
  .allocation-row-values { text-align: left; }
}
@media (max-width: 800px) {
  .utility-row { flex-direction: column; align-items: stretch; }
  .utility-actions { flex-direction: column; align-items: stretch; }
  .nav-row { flex-wrap: wrap; }
  .brand-block h1 { font-size: 34px; }
}
"""
