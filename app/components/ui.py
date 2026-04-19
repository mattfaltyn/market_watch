from __future__ import annotations

from datetime import datetime
from typing import Callable, Iterable

import dash
from dash import dash_table, dcc, html
import pandas as pd
import plotly.graph_objects as go

from app.models import AlertFlag, MetricCard


COLOR_MAP = {
    "positive": "#177245",
    "negative": "#a6403b",
    "warning": "#a66b12",
    "neutral": "#234463",
    "market": "#234463",
    "rates": "#a66b12",
}


def _format_timestamp(value: object) -> str:
    if value is None:
        return "Unavailable"
    if isinstance(value, pd.Timestamp):
        value = value.to_pydatetime()
    if isinstance(value, datetime):
        return value.strftime("%b %d, %Y")
    return str(value)


def app_shell(
    children,
    page_title: str,
    active_page: str = "kiss-overview",
    status_meta: dict | None = None,
) -> html.Div:
    status_meta = status_meta or {}
    nav = [
        ("KISS Overview", "/", "kiss-overview"),
        ("Implementation", "/implementation", "implementation"),
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
                                    html.H1("KISS Portfolio"),
                                    html.P(page_title, className="subtitle"),
                                ],
                            ),
                            html.Div(
                                className="utility-actions",
                                children=[
                                    html.Div(
                                        className="status-strip",
                                        children=[
                                            _status_item("Source", str(status_meta.get("source", "defeatbeta-api"))),
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
        children=[
            html.Span(label, className="status-label"),
            html.Span(value, className="status-value"),
        ],
    )


def metric_card(card: MetricCard) -> html.Div:
    return html.Div(
        className=f"metric-card metric-{card.variant} tone-{card.tone}",
        children=[
            html.Div(card.label, className="metric-label"),
            html.Div(card.value, className="metric-value"),
            html.Div(card.delta or "", className="metric-delta"),
        ],
    )


def benchmark_card(symbol: str, price: str, delta: str, tone: str) -> html.Div:
    return html.Div(
        className=f"metric-card metric-compact benchmark-card tone-{tone}",
        children=[
            html.Div(symbol, className="benchmark-symbol"),
            html.Div(price, className="benchmark-price"),
            html.Div(delta, className="benchmark-returns"),
        ],
    )


def badge(text: str, tone: str = "neutral") -> html.Span:
    return html.Span(text, className=f"badge tone-{tone}")


def error_box(errors: list[str]) -> html.Div | None:
    if not errors:
        return None
    return html.Div(
        [html.Strong("Data warnings"), html.Ul([html.Li(error) for error in errors])],
        className="error-box",
    )


def fatal_error_page(title: str, errors: list[str], guidance: list[str] | None = None) -> html.Div:
    guidance = guidance or []
    return app_shell(
        [
            html.Div(
                className="section",
                children=[
                    html.H2(title),
                    html.P("The dashboard could not finish loading its data."),
                    error_box(errors) or html.Div("Unknown error", className="error-box"),
                    html.H3("Troubleshooting"),
                    html.Ul(className="insight-list", children=[html.Li(item) for item in guidance]),
                ],
            )
        ],
        page_title="Dashboard load error",
        active_page="kiss-overview",
        status_meta={"scope": "Load failure"},
    )


def make_pie_chart(labels: list[str], values: list[float], title: str) -> dcc.Graph | html.Div:
    if not labels or not values:
        return html.Div("Data unavailable for this view.", className="empty-state")
    figure = go.Figure(
        data=[
            go.Pie(
                labels=labels,
                values=values,
                hole=0.55,
                marker={"colors": ["#234463", "#5c87b0", "#d38b22", "#d8dddf"]},
                textinfo="label+percent",
            )
        ]
    )
    figure.update_layout(
        title={"text": title, "x": 0.02, "xanchor": "left"},
        margin={"l": 10, "r": 10, "t": 52, "b": 10},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=340,
        showlegend=False,
    )
    return dcc.Graph(figure=figure, config={"displayModeBar": False}, className="chart")


def _series_color(semantic: str) -> str:
    return COLOR_MAP.get(semantic, COLOR_MAP["neutral"])


def make_line_chart(
    frame: pd.DataFrame,
    x: str,
    y_columns: list[str],
    title: str,
    semantic: str = "market",
) -> dcc.Graph | html.Div:
    usable = frame.copy()
    if usable.empty or x not in usable.columns or not any(column in usable.columns for column in y_columns):
        return html.Div("Data unavailable for this view.", className="empty-state")
    figure = go.Figure()
    line_color = _series_color(semantic)
    for column in y_columns:
        if column in usable.columns:
            figure.add_trace(
                go.Scatter(
                    x=usable[x],
                    y=usable[column],
                    mode="lines",
                    name=column.replace("_", " ").title(),
                    line={"width": 3 if len(y_columns) == 1 else 2, "color": line_color if len(y_columns) == 1 else None},
                    fill="tozeroy" if len(y_columns) == 1 else None,
                    fillcolor=(
                        "rgba(35,68,99,0.08)"
                        if semantic == "market" and len(y_columns) == 1
                        else "rgba(166,107,18,0.10)"
                        if semantic in {"warning", "rates"} and len(y_columns) == 1
                        else None
                    ),
                )
            )
    figure.update_layout(
        title={"text": title, "x": 0.02, "xanchor": "left"},
        margin={"l": 14, "r": 14, "t": 52, "b": 24},
        template="plotly_white",
        height=320,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        hoverlabel={"bgcolor": "#12253b", "font_color": "#f7f2e9"},
        legend={"orientation": "h", "y": 1.08, "x": 0.02},
    )
    figure.update_xaxes(showgrid=False, zeroline=False, linecolor="rgba(35,68,99,0.12)", tickfont={"color": "#5f7388"})
    figure.update_yaxes(showgrid=True, gridcolor="rgba(35,68,99,0.08)", zeroline=False, tickfont={"color": "#5f7388"})
    return dcc.Graph(figure=figure, config={"displayModeBar": False}, className="chart")


def make_bar_chart(frame: pd.DataFrame, x: str, title: str, semantic: str = "market") -> dcc.Graph | html.Div:
    if frame.empty or x not in frame.columns:
        return html.Div("Data unavailable for this view.", className="empty-state")
    value_columns = [column for column in frame.columns if column not in {"symbol", "report_date", x}]
    if not value_columns:
        return html.Div("Data unavailable for this view.", className="empty-state")
    latest = frame.sort_values(x).tail(1)
    melted = latest.melt(id_vars=[x], value_vars=value_columns, var_name="series", value_name="value")
    figure = go.Figure(go.Bar(x=melted["series"], y=melted["value"], marker_color=_series_color(semantic)))
    figure.update_layout(
        title={"text": title, "x": 0.02, "xanchor": "left"},
        margin={"l": 14, "r": 14, "t": 52, "b": 24},
        template="plotly_white",
        height=320,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    figure.update_xaxes(showgrid=False, tickfont={"color": "#5f7388"})
    figure.update_yaxes(showgrid=True, gridcolor="rgba(35,68,99,0.08)", tickfont={"color": "#5f7388"})
    return dcc.Graph(figure=figure, config={"displayModeBar": False}, className="chart")


def _format_numeric(value: object, column: str) -> object:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "—"
    if isinstance(value, pd.Timestamp):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float)):
        if "return" in column or "spread" in column or "margin" in column or "growth" in column:
            return f"{value:+.1%}"
        if "days_to" in column:
            return f"{value:.0f}"
        if "count" in column or "alert" in column:
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
        return html.Div("Data unavailable for this section.", className="empty-state")
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
        page_size=10,
        style_table={"overflowX": "auto", "border": "1px solid rgba(35,68,99,0.08)", "borderRadius": "18px"},
        style_cell={
            "textAlign": "left",
            "padding": "12px 14px",
            "fontFamily": "\"IBM Plex Sans\", \"Avenir Next\", sans-serif",
            "fontSize": 13,
            "backgroundColor": "rgba(255,255,255,0.98)",
            "color": "#173047",
            "border": "none",
            "borderBottom": "1px solid rgba(35,68,99,0.06)",
            "maxWidth": 220,
            "whiteSpace": "normal",
        },
        style_cell_conditional=[{"if": {"column_id": column}, "textAlign": "right"} for column in numeric_columns],
        style_data_conditional=[{"if": {"row_index": "odd"}, "backgroundColor": "rgba(247,242,233,0.65)"}],
        style_header={
            "fontWeight": 700,
            "backgroundColor": "#eef3f7",
            "color": "#5f7388",
            "textTransform": "uppercase",
            "fontSize": 11,
            "letterSpacing": "0.08em",
            "borderBottom": "1px solid rgba(35,68,99,0.12)",
        },
    )


def alert_list(flags: Iterable[AlertFlag]) -> html.Div:
    rendered = [
        html.Li(
            className="alert-item",
            children=[
                badge(flag.severity, tone="warning" if flag.severity == "medium" else "negative" if flag.severity == "high" else "neutral"),
                html.Span(flag.message, className="alert-text"),
            ],
        )
        for flag in flags
    ]
    if not rendered:
        return html.Div("No active alerts", className="empty-state")
    return html.Div([html.H3("Alerts"), html.Ul(className="alert-list", children=rendered)], className="section")


def insight_list(items: list[str], title: str) -> html.Div:
    return html.Div(
        className="section",
        children=[
            html.H3(title),
            html.Ul(className="insight-list", children=[html.Li(item) for item in items]),
        ],
    )


def feed_panel(title: str, frame: pd.DataFrame, title_column: str, secondary_columns: list[str]) -> html.Div:
    if frame.empty or title_column not in frame.columns:
        return html.Div([html.H3(title), html.Div("Data unavailable for this section.", className="empty-state")], className="section")
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
    return html.Div([html.H3(title), html.Div(className="feed-list", children=items)], className="section")


APP_CSS = """
:root {
  --bg: #f4efe7;
  --bg-glow: #e9f0f6;
  --surface: rgba(255, 255, 255, 0.95);
  --surface-soft: rgba(247, 242, 233, 0.72);
  --text: #182c40;
  --text-muted: #61758a;
  --text-soft: #8a99a7;
  --border: rgba(24, 44, 64, 0.10);
  --shadow: 0 20px 50px rgba(21, 39, 56, 0.08);
  --shadow-soft: 0 10px 30px rgba(21, 39, 56, 0.05);
  --radius-xl: 28px;
  --radius-lg: 22px;
  --radius-md: 16px;
}
body {
  margin: 0;
  font-family: "IBM Plex Sans", "Avenir Next", sans-serif;
  background:
    radial-gradient(circle at top left, rgba(233, 240, 246, 0.95) 0%, rgba(233, 240, 246, 0) 38%),
    linear-gradient(180deg, var(--bg) 0%, var(--bg-glow) 100%);
  color: var(--text);
}
a {
  color: #12395b;
  text-decoration: none;
  font-weight: 600;
}
.app-shell {
  min-height: 100vh;
}
.app-frame {
  position: sticky;
  top: 0;
  z-index: 10;
  padding: 18px 24px 0;
  background: linear-gradient(180deg, rgba(244, 239, 231, 0.9) 0%, rgba(244, 239, 231, 0.55) 100%);
  backdrop-filter: blur(16px);
}
.utility-row {
  max-width: 1380px;
  margin: 0 auto;
  padding: 18px 22px 14px;
  display: flex;
  gap: 20px;
  justify-content: space-between;
  align-items: center;
  background: rgba(255, 255, 255, 0.78);
  border: 1px solid var(--border);
  border-radius: var(--radius-xl) var(--radius-xl) 0 0;
  box-shadow: var(--shadow-soft);
}
.brand-block h1 {
  margin: 0;
  font-size: 54px;
  letter-spacing: -0.06em;
}
.subtitle {
  margin: 6px 0 0;
  color: var(--text-muted);
  font-size: 18px;
}
.utility-actions {
  display: flex;
  gap: 16px;
  align-items: center;
}
.status-strip {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
}
.status-item {
  display: flex;
  flex-direction: column;
  gap: 3px;
  padding-right: 16px;
  border-right: 1px solid rgba(24, 44, 64, 0.08);
}
.status-item:last-child {
  border-right: none;
}
.status-label {
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--text-soft);
}
.status-value {
  font-size: 13px;
  color: var(--text);
  font-weight: 600;
}
.refresh-button {
  border: none;
  border-radius: 999px;
  background: linear-gradient(135deg, #173a56 0%, #234463 100%);
  color: white;
  padding: 12px 18px;
  font-weight: 700;
  cursor: pointer;
  box-shadow: 0 12px 28px rgba(35, 68, 99, 0.2);
}
.nav-row {
  max-width: 1380px;
  margin: 0 auto;
  padding: 14px 22px 18px;
  display: flex;
  gap: 10px;
  background: rgba(255, 255, 255, 0.78);
  border: 1px solid var(--border);
  border-top: none;
  border-radius: 0 0 var(--radius-xl) var(--radius-xl);
  box-shadow: var(--shadow-soft);
}
.nav-pill {
  padding: 10px 16px;
  border-radius: 999px;
  color: var(--text-muted);
  background: rgba(244, 239, 231, 0.6);
}
.nav-pill.is-active {
  background: #173a56;
  color: white;
}
.page-body-wrap {
  padding: 28px 24px 52px;
}
.page-body {
  max-width: 1380px;
  margin: 0 auto;
}
.hero-grid {
  display: grid;
  grid-template-columns: 1.25fr 1fr;
  gap: 18px;
}
.kpi-strip {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
  margin-top: 18px;
}
.section-heading {
  display: flex;
  justify-content: space-between;
  align-items: end;
  margin: 26px 0 14px;
}
.section-heading h2 {
  margin: 0;
  font-size: 30px;
  letter-spacing: -0.03em;
}
.section-heading p {
  margin: 0;
  color: var(--text-muted);
}
.market-tape {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
}
.info-grid {
  display: grid;
  grid-template-columns: 1.35fr 1fr;
  gap: 18px;
  margin-top: 18px;
}
.section, .metric-card, .error-box {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 20px;
  box-shadow: var(--shadow);
  border-top: 4px solid rgba(24, 44, 64, 0.14);
}
.metric-compact {
  min-height: 100px;
}
.metric-kpi {
  min-height: 132px;
}
.metric-hero {
  min-height: 160px;
}
.tone-positive { border-top-color: #177245; }
.tone-negative { border-top-color: #a6403b; }
.tone-warning { border-top-color: #a66b12; }
.tone-neutral, .tone-market { border-top-color: #234463; }
.tone-rates { border-top-color: #a66b12; }
.metric-label {
  font-size: 11px;
  text-transform: uppercase;
  color: var(--text-soft);
  letter-spacing: 0.12em;
}
.metric-value {
  font-size: 24px;
  font-weight: 800;
  margin-top: 10px;
  letter-spacing: -0.04em;
}
.metric-compact .metric-value {
  font-size: 20px;
}
.metric-delta {
  margin-top: 10px;
  color: var(--text-muted);
  line-height: 1.45;
}
.hero-card {
  min-height: 220px;
}
.hero-label {
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: var(--text-soft);
  margin-bottom: 12px;
}
.hero-value {
  font-size: 46px;
  line-height: 1;
  font-weight: 800;
  letter-spacing: -0.05em;
}
.hero-summary {
  margin-top: 14px;
  font-size: 17px;
  line-height: 1.55;
  color: var(--text-muted);
}
.hero-footer {
  margin-top: 20px;
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}
.briefing-card h3,
.section h3 {
  margin: 0 0 14px;
  font-size: 24px;
  letter-spacing: -0.03em;
}
.briefing-list,
.insight-list,
.alert-list {
  margin: 0;
  padding-left: 20px;
}
.briefing-list li,
.insight-list li {
  margin-bottom: 12px;
  color: var(--text-muted);
  line-height: 1.55;
}
.two-col {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 18px;
  margin-top: 18px;
}
.three-col {
  display: grid;
  grid-template-columns: 1.25fr 1fr 0.85fr;
  gap: 18px;
  margin-top: 18px;
}
.badge {
  display: inline-block;
  padding: 6px 10px;
  border-radius: 999px;
  color: white;
  font-size: 10px;
  text-transform: uppercase;
  font-weight: 700;
  letter-spacing: 0.08em;
}
.badge.tone-positive { background: #177245; }
.badge.tone-negative { background: #a6403b; }
.badge.tone-warning { background: #a66b12; }
.badge.tone-neutral,
.badge.tone-market { background: #234463; }
.badge.tone-rates { background: #a66b12; }
.empty-state {
  padding: 32px 20px;
  color: var(--text-muted);
  background: var(--surface-soft);
  border: 1px dashed rgba(24, 44, 64, 0.12);
  border-radius: var(--radius-md);
}
.error-box {
  margin-bottom: 18px;
}
.benchmark-card {
  min-height: 128px;
}
.benchmark-symbol {
  font-size: 11px;
  text-transform: uppercase;
  color: var(--text-soft);
  letter-spacing: 0.12em;
}
.benchmark-price {
  margin-top: 10px;
  font-size: 27px;
  font-weight: 800;
  letter-spacing: -0.04em;
}
.benchmark-returns {
  margin-top: 10px;
  color: var(--text-muted);
}
.chart {
  margin-top: -6px;
}
.feed-list {
  display: grid;
  gap: 10px;
}
.feed-item {
  padding: 14px 16px;
  border-radius: 14px;
  background: rgba(244, 239, 231, 0.58);
  border: 1px solid rgba(24, 44, 64, 0.06);
}
.feed-title {
  font-weight: 700;
  color: var(--text);
  line-height: 1.45;
}
.feed-meta {
  margin-top: 4px;
  font-size: 13px;
  color: var(--text-muted);
}
.alert-item {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
}
.alert-text {
  color: var(--text-muted);
}
.ticker-header {
  display: grid;
  grid-template-columns: 1.1fr 1fr;
  gap: 18px;
  margin-bottom: 18px;
}
.ticker-summary {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.ticker-symbol {
  font-size: 13px;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: var(--text-soft);
}
.ticker-company {
  font-size: 34px;
  font-weight: 800;
  letter-spacing: -0.04em;
}
.meta-row {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}
.card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 14px;
}
@media (max-width: 1180px) {
  .market-tape,
  .kpi-strip,
  .three-col,
  .ticker-header {
    grid-template-columns: 1fr;
  }
}
@media (max-width: 900px) {
  .hero-grid,
  .two-col,
  .info-grid,
  .utility-row {
    grid-template-columns: 1fr;
  }
  .utility-row {
    display: grid;
  }
  .utility-actions {
    display: grid;
  }
  .brand-block h1 {
    font-size: 42px;
  }
}
"""
