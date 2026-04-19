"""Plotly chart helpers using shared theme."""

from __future__ import annotations

from typing import Any, Sequence

import pandas as pd
import plotly.graph_objects as go
from dash import dcc, html

from app.components.theme import plotly_template, series_color


def _empty_chart_state(message: str = "Unavailable") -> html.Div:
    return html.Div(message, className="empty-state")


def sparkline_chart(
    values: Sequence[float] | pd.Series,
    semantic: str = "market",
    height: int = 44,
) -> dcc.Graph | html.Div:
    series = pd.Series(list(values), dtype=float).dropna()
    if series.empty:
        return _empty_chart_state("Unavailable")
    fig = go.Figure(
        go.Scatter(
            x=list(range(len(series))),
            y=series,
            mode="lines",
            line={"color": series_color(0, semantic), "width": 2},
            fill="tozeroy",
            fillcolor="rgba(91,192,255,0.10)" if semantic == "market" else "rgba(51,209,122,0.10)" if semantic == "positive" else "rgba(255,159,67,0.10)",
        )
    )
    fig.update_layout(
        template=plotly_template(),
        margin={"l": 0, "r": 0, "t": 0, "b": 0},
        height=height,
        showlegend=False,
    )
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    return dcc.Graph(figure=fig, config={"displayModeBar": False}, className="sparkline")


def make_line_chart(
    frame: pd.DataFrame,
    x: str,
    y_columns: list[str],
    title: str,
    semantic: str = "market",
    compact: bool = False,
    *,
    x_axis_title: str | None = None,
    y_axis_title: str | None = None,
    y_reference: float | None = None,
    extra_hlines: list[tuple[float, str]] | None = None,
    range_selector: bool = False,
    secondary_y: str | None = None,
) -> dcc.Graph | html.Div:
    usable = frame.copy()
    if usable.empty or x not in usable.columns or not any(column in usable.columns for column in y_columns):
        return _empty_chart_state()
    fig = go.Figure()
    for index, column in enumerate(y_columns):
        if column not in usable.columns:
            continue
        yaxis = "y2" if secondary_y and column == secondary_y else "y"
        fig.add_trace(
            go.Scatter(
                x=usable[x],
                y=usable[column],
                mode="lines",
                name=column.replace("_", " ").title(),
                line={"width": 2.5 if index == 0 else 1.8, "color": series_color(index, semantic if index == 0 else None)},
                fill="tozeroy" if len(y_columns) == 1 and yaxis == "y" else None,
                fillcolor="rgba(91,192,255,0.08)" if semantic == "market" and len(y_columns) == 1 else None,
                yaxis=yaxis,
            )
        )
    if y_reference is not None:
        fig.add_hline(y=y_reference, line_dash="dash", line_color="rgba(140,163,186,0.6)", line_width=1)
    for y_val, ann in extra_hlines or []:
        fig.add_hline(y=y_val, line_dash="dot", line_color="rgba(255,179,71,0.7)", line_width=1, annotation_text=ann, annotation_position="bottom right")

    layout_updates: dict[str, Any] = {
        "template": plotly_template(),
        "title": {"text": title, "x": 0.03, "xanchor": "left", "font": {"color": "#e6f1ff", "size": 14}} if title else None,
        "margin": {"l": 50, "r": 50 if secondary_y else 10, "t": 42 if title else 8, "b": 20},
        "height": 180 if compact else 280,
        "showlegend": not compact and len(y_columns) > 1,
    }
    if secondary_y:
        layout_updates["yaxis2"] = {
            "overlaying": "y",
            "side": "right",
            "showgrid": False,
            "tickfont": {"color": "#7f96ad"},
        }
    fig.update_layout(**layout_updates)
    fig.update_xaxes(showgrid=False, zeroline=False, color="#7f96ad", title=x_axis_title or "")
    fig.update_yaxes(showgrid=True, zeroline=True, color="#7f96ad", title=y_axis_title or "")
    if range_selector:
        fig.update_xaxes(
            rangeslider_visible=False,
            rangeselector={
                "buttons": [
                    {"count": 1, "label": "1M", "step": "month", "stepmode": "backward"},
                    {"count": 3, "label": "3M", "step": "month", "stepmode": "backward"},
                    {"count": 6, "label": "6M", "step": "month", "stepmode": "backward"},
                    {"count": 1, "label": "YTD", "step": "year", "stepmode": "todate"},
                    {"count": 1, "label": "1Y", "step": "year", "stepmode": "backward"},
                    {"step": "all", "label": "MAX"},
                ]
            },
        )
    return dcc.Graph(figure=fig, config={"displayModeBar": False}, className="chart")


def make_bar_chart(
    frame: pd.DataFrame,
    x: str,
    title: str,
    semantic: str = "market",
    y_axis_title: str | None = None,
) -> dcc.Graph | html.Div:
    if frame.empty or x not in frame.columns:
        return _empty_chart_state()
    value_columns = [column for column in frame.columns if column not in {"symbol", "report_date", x}]
    if not value_columns:
        return _empty_chart_state()
    latest = frame.sort_values(x).tail(1)
    melted = latest.melt(id_vars=[x], value_vars=value_columns, var_name="series", value_name="value")
    fig = go.Figure(
        go.Bar(
            x=melted["series"],
            y=melted["value"],
            marker_color=[series_color(0, semantic)] * len(melted),
            marker_line={"color": "#081521", "width": 1.5},
        )
    )
    fig.update_layout(
        template=plotly_template(),
        title={"text": title, "x": 0.03, "xanchor": "left", "font": {"color": "#e6f1ff", "size": 14}},
        margin={"l": 50, "r": 10, "t": 42, "b": 20},
        height=260,
    )
    fig.update_xaxes(showgrid=False, color="#7f96ad")
    fig.update_yaxes(showgrid=True, gridcolor="rgba(140,163,186,0.14)", color="#7f96ad", title=y_axis_title or "")
    return dcc.Graph(figure=fig, config={"displayModeBar": False}, className="chart")


def yield_curve_bar(labels: list[str], values: list[float | None], title: str) -> dcc.Graph | html.Div:
    if not labels or not values:
        return _empty_chart_state()
    ys = [float(v) if v is not None else None for v in values]
    if all(v is None for v in ys):
        return _empty_chart_state()
    fig = go.Figure(
        go.Bar(
            x=labels,
            y=ys,
            marker_color=series_color(0, "rates"),
            marker_line={"color": "#081521", "width": 1.5},
        )
    )
    fig.update_layout(
        template=plotly_template(),
        title={"text": title, "x": 0.03, "xanchor": "left", "font": {"color": "#e6f1ff", "size": 14}},
        margin={"l": 50, "r": 10, "t": 42, "b": 20},
        height=220,
    )
    fig.update_yaxes(title="Yield", tickformat=".2%")
    return dcc.Graph(figure=fig, config={"displayModeBar": False}, className="chart")


def make_pie_chart(labels: list[str], values: list[float], title: str) -> dcc.Graph | html.Div:
    from app.components.theme import SLEEVE_COLORS

    if not labels or not values:
        return _empty_chart_state()
    fig = go.Figure(
        data=[
            go.Pie(
                labels=labels,
                values=values,
                hole=0.68,
                marker={
                    "colors": [SLEEVE_COLORS.get(label.upper(), "#5bc0ff") for label in labels],
                    "line": {"color": "#081521", "width": 2},
                },
                textinfo="percent",
                textfont={"color": "#e6f1ff", "size": 13},
            )
        ]
    )
    fig.update_layout(
        template=plotly_template(),
        title={"text": title, "x": 0.03, "xanchor": "left", "font": {"color": "#e6f1ff", "size": 14}},
        margin={"l": 10, "r": 10, "t": 44, "b": 10},
        height=300,
        showlegend=False,
    )
    return dcc.Graph(figure=fig, config={"displayModeBar": False}, className="chart")


def exposure_gauge(
    value: float | None,
    label: str,
    tone: str = "market",
    *,
    step_ranges: list[tuple[float, float]] | None = None,
) -> html.Div:
    if value is None:
        return html.Div(
            className="terminal-gauge gauge-panel",
            children=[
                html.Div(label, className="mini-panel-label"),
                _empty_chart_state("Unavailable"),
            ],
        )
    from app.components.theme import series_color as _series_color

    mapped = "neutral_state" if tone == "neutral" else tone
    steps = []
    if step_ranges:
        for lo, hi in step_ranges:
            steps.append({"range": [lo, hi], "color": "rgba(140,163,186,0.18)"})
    else:
        steps = [
            {"range": [0, 35], "color": "rgba(140,163,186,0.12)"},
            {"range": [35, 70], "color": "rgba(140,163,186,0.20)"},
            {"range": [70, 100], "color": "rgba(140,163,186,0.28)"},
        ]
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=max(0.0, min(value * 100, 100.0)),
            number={"suffix": "%", "font": {"size": 28, "color": "#f5fbff"}},
            gauge={
                "shape": "angular",
                "axis": {"range": [0, 100], "tickcolor": "#54718f", "tickwidth": 1},
                "bar": {"color": _series_color(0, mapped)},
                "bgcolor": "rgba(18,32,46,0.65)",
                "borderwidth": 0,
                "steps": steps,
            },
        )
    )
    fig.update_layout(
        margin={"l": 12, "r": 12, "t": 10, "b": 0},
        paper_bgcolor="rgba(0,0,0,0)",
        height=180,
    )
    return html.Div(
        className="terminal-gauge",
        children=[html.Div(label, className="mini-panel-label"), dcc.Graph(figure=fig, config={"displayModeBar": False})],
    )


def price_with_mas(
    frame: pd.DataFrame,
    symbol: str,
    windows: dict[str, int],
    *,
    volume_column: str | None = None,
    range_selector: bool = True,
) -> dcc.Graph | html.Div:
    usable = frame.copy()
    if usable.empty or "close" not in usable.columns or "report_date" not in usable.columns:
        return _empty_chart_state()
    usable = usable.sort_values("report_date")
    close = pd.to_numeric(usable["close"], errors="coerce")
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=usable["report_date"],
            y=close,
            name="Close",
            line={"color": series_color(0, "market"), "width": 2},
        )
    )
    for i, (name, w) in enumerate(windows.items()):
        if len(close.dropna()) >= w:
            ma = close.rolling(window=w, min_periods=w).mean()
            fig.add_trace(
                go.Scatter(
                    x=usable["report_date"],
                    y=ma,
                    name=name,
                    line={"color": series_color(i + 1, None), "width": 1.2, "dash": "dot"},
                )
            )
    if volume_column and volume_column in usable.columns:
        vol = pd.to_numeric(usable[volume_column], errors="coerce")
        fig.add_trace(
            go.Bar(
                x=usable["report_date"],
                y=vol,
                name="Volume",
                yaxis="y2",
                marker_color="rgba(127,150,173,0.35)",
            )
        )
        fig.update_layout(
            yaxis2={
                "overlaying": "y",
                "side": "right",
                "showgrid": False,
                "title": "Volume",
            }
        )
    fig.update_layout(
        template=plotly_template(),
        title={"text": f"{symbol} Price", "x": 0.03, "xanchor": "left", "font": {"color": "#e6f1ff", "size": 14}},
        margin={"l": 50, "r": 60 if volume_column else 10, "t": 42, "b": 20},
        height=360,
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02},
    )
    fig.update_yaxes(title="Price ($)", zeroline=True)
    fig.update_xaxes(title="Date")
    if range_selector:
        fig.update_xaxes(
            rangeslider_visible=False,
            rangeselector={
                "buttons": [
                    {"count": 1, "label": "1M", "step": "month", "stepmode": "backward"},
                    {"count": 3, "label": "3M", "step": "month", "stepmode": "backward"},
                    {"count": 6, "label": "6M", "step": "month", "stepmode": "backward"},
                    {"count": 1, "label": "YTD", "step": "year", "stepmode": "todate"},
                    {"count": 1, "label": "1Y", "step": "year", "stepmode": "backward"},
                    {"step": "all", "label": "MAX"},
                ]
            },
        )
    return dcc.Graph(figure=fig, config={"displayModeBar": False}, className="chart")
