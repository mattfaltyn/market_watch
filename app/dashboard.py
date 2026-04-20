from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pandas as pd
import plotly.graph_objects as go
from dash import dcc, html
import dash_mantine_components as dmc

from app.components.theme import (
    ACCENT_PRIMARY,
    ACCENT_SECONDARY,
    MOVE_DOWN,
    MOVE_UP,
    TEXT_LOW,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    THEME,
    plotly_template,
)
from app.config import AppConfig
from app.data.bitcoin_client import BitcoinDataClient, history_to_records, records_to_history
from app.metrics import RangeKey
from app.models import BitcoinSnapshot, DataResult

RANGE_OPTIONS: list[RangeKey] = ["1D", "7D", "30D", "90D", "1Y", "ALL"]
MDASH = "\u2014"


def coalesce_history(prior_records: list[dict[str, Any]] | None, result: DataResult) -> tuple[pd.DataFrame, list[str]]:
    errs = list(result.errors)
    if isinstance(result.data, pd.DataFrame) and not result.data.empty:
        return result.data, errs
    prior_df = records_to_history(prior_records or [])
    if not prior_df.empty:
        return prior_df, errs
    return pd.DataFrame(), errs


def fmt_usd(val: float | None) -> str:
    if val is None or (isinstance(val, float) and (val != val)):  # nan
        return MDASH
    s = f"{val:,.2f}"
    return f"${s}"


def fmt_pct(val: float | None, *, signed: bool = True) -> str:
    if val is None or (isinstance(val, float) and (val != val)):
        return MDASH
    pct = val * 100.0
    if signed and pct > 0:
        return f"+{pct:.2f}%"
    return f"{pct:.2f}%"


def fmt_vol(val: float | None) -> str:
    if val is None or (isinstance(val, float) and (val != val)):
        return MDASH
    if val >= 1e9:
        return f"{val / 1e9:.2f}B"
    if val >= 1e6:
        return f"{val / 1e6:.2f}M"
    if val >= 1e3:
        return f"{val / 1e3:.2f}K"
    return f"{val:.0f}"


def _paper(children: Any, **props: Any) -> dmc.Paper:
    extra = props.pop("className", None)
    cls = f"mw-card {extra}".strip() if extra else "mw-card"
    return dmc.Paper(
        children=children,
        p="lg",
        className=cls,
        style={"backgroundColor": "var(--bg-secondary)", "borderColor": "rgba(63,60,89,0.5)"},
        **props,
    )


def build_error_banner(errors: list[str]) -> Any:
    if not errors:
        return html.Div(id="error-banner", style={"display": "none"})
    return dmc.Alert(
        title="Data notice",
        children=[html.Div(e) for e in errors],
        color="yellow",
        variant="light",
        id="error-banner",
        className="mw-fade-in",
        mb="md",
    )


def build_price_figure(snap: BitcoinSnapshot) -> go.Figure:
    ch = snap.chart
    template = plotly_template()
    fig = go.Figure()
    fig.update_layout(template=template)
    if not ch.report_dates:
        fig.update_layout(annotations=[{"text": "No chart data", "xref": "paper", "yref": "paper", "showarrow": False}])
        return fig
    fig.add_trace(
        go.Scatter(
            x=ch.report_dates,
            y=ch.close,
            mode="lines",
            name="BTC",
            line={"color": ACCENT_PRIMARY, "width": 2},
            fill="tozeroy",
            fillcolor="rgba(252,152,65,0.08)",
        )
    )
    if any(v is not None for v in ch.ma20):
        fig.add_trace(
            go.Scatter(
                x=ch.report_dates,
                y=[x if x is not None else None for x in ch.ma20],
                mode="lines",
                name="MA 20",
                line={"color": ACCENT_SECONDARY, "width": 1.2, "dash": "dot"},
            )
        )
    if any(v is not None for v in ch.ma50):
        fig.add_trace(
            go.Scatter(
                x=ch.report_dates,
                y=[x if x is not None else None for x in ch.ma50],
                mode="lines",
                name="MA 50",
                line={"color": TEXT_MUTED, "width": 1, "dash": "dash"},
            )
        )
    if len(ch.report_dates) == 1:
        fig.update_traces(mode="markers+lines")
    fig.update_layout(
        template=template,
        showlegend=len(ch.report_dates) > 1,
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "right", "x": 1},
        hovermode="x unified",
    )
    return fig


def create_app_layout(config: AppConfig) -> Any:
    """Root layout: all callback Inputs must exist before first render."""
    default_range = config.dashboard.default_range
    if default_range not in RANGE_OPTIONS:
        default_range = "90D"
    return dmc.MantineProvider(
        theme=THEME,
        children=[
            dcc.Location(id="url", pathname="/"),
            dcc.Store(id="refresh-state", data={"refresh": 0}),
            dcc.Store(id="history-store", data={}),
            dmc.Container(
                fluid=True,
                className="mw-shell",
                px="md",
                children=[
                    html.Div(id="error-banner-container"),
                    html.Div(
                        id="section-header",
                        className="mw-header-row mw-fade-in",
                        children=[
                            dmc.Group(
                                justify="space-between",
                                align="flex-start",
                                wrap="nowrap",
                                children=[
                                    dmc.Stack(
                                        gap=4,
                                        children=[
                                            dmc.Title(
                                                "Bitcoin Market Watch",
                                                order=1,
                                                className="mw-font-heading",
                                                c=TEXT_PRIMARY,
                                            ),
                                            dmc.Text(
                                                "Local dashboard · Yahoo Finance (yfinance) · Daily closes",
                                                size="sm",
                                                c=TEXT_MUTED,
                                                id="header-sublabel",
                                            ),
                                        ],
                                    ),
                                    dmc.Stack(
                                        gap="xs",
                                        align="flex-end",
                                        children=[
                                            dmc.Text(
                                                "Updated —",
                                                size="xs",
                                                c=TEXT_LOW,
                                                id="header-updated",
                                            ),
                                            dmc.Button("Refresh", id="refresh-button", variant="filled", color="orange", n_clicks=0),
                                        ],
                                    ),
                                ],
                            )
                        ],
                    ),
                    html.Div(
                        className="mw-range-toolbar mw-fade-in",
                        children=[
                            dmc.Group(
                                justify="space-between",
                                align="center",
                                mb="md",
                                children=[
                                    dmc.Text("Chart range", size="sm", fw=600, c=TEXT_MUTED),
                                    dmc.SegmentedControl(
                                        id="range-select",
                                        data=[{"value": r, "label": r} for r in RANGE_OPTIONS],
                                        value=default_range,
                                        color="orange",
                                        size="sm",
                                        className="mw-range-pills",
                                    ),
                                ],
                            )
                        ],
                    ),
                    html.Div(id="page-container"),
                ],
            ),
        ],
    )


def build_empty_state() -> Any:
    return dmc.Container(
        fluid=True,
        className="mw-shell",
        children=[
            dmc.Stack(
                align="center",
                justify="center",
                gap="md",
                style={"minHeight": "60vh"},
                children=[
                    dmc.Title("Bitcoin Market Watch", order=2, c=TEXT_PRIMARY, className="mw-font-heading"),
                    dmc.Text(
                        "No BTC-USD history is available yet. Check your connection to Yahoo Finance and try Refresh.",
                        c=TEXT_MUTED,
                        ta="center",
                        maw=480,
                        id="empty-state",
                    ),
                ],
            )
        ],
    )


def build_page_content(snap: BitcoinSnapshot) -> Any:
    st = snap.stats
    hero_sub = []
    if st.dist_from_ath_pct is not None:
        hero_sub.append(
            dmc.Text(
                f"Trading {fmt_pct(st.dist_from_ath_pct, signed=True)} vs all-time high",
                size="sm",
                c=TEXT_MUTED,
                id="hero-ath-line",
            )
        )
    if st.vol_30d_ann is not None:
        hero_sub.append(
            dmc.Text(
                f"30D realized volatility {fmt_pct(st.vol_30d_ann, signed=False)}",
                size="sm",
                c=TEXT_MUTED,
                id="hero-vol-line",
            )
        )

    chg = snap.change_1d_pct
    chg_color = TEXT_SECONDARY
    if chg is not None:
        chg_color = MOVE_UP if chg >= 0 else MOVE_DOWN

    fig = build_price_figure(snap)
    range_note = ""
    if snap.range_key == "1D":
        range_note = "Daily close context (intraday not included)."

    stat_cards = [
        _stat_cell("7D return", fmt_pct(st.ret_7d), "Trailing week vs anchor close"),
        _stat_cell("30D return", fmt_pct(st.ret_30d), "Trailing month"),
        _stat_cell("YTD return", fmt_pct(st.ret_ytd), "Year to date"),
        _stat_cell("1Y return", fmt_pct(st.ret_1y), "Trailing year"),
        _stat_cell("From ATH", fmt_pct(st.dist_from_ath_pct) if st.dist_from_ath_pct is not None else MDASH, "Distance from all-time high"),
        _stat_cell("30D realized vol", fmt_pct(st.vol_30d_ann, signed=False) if st.vol_30d_ann is not None else MDASH, "Annualized, daily returns"),
    ]

    vol_card = _paper(
        [
            dmc.Text("Volume", size="sm", fw=600, c=TEXT_SECONDARY),
            dmc.Group(
                gap="xl",
                mt="xs",
                children=[
                    dmc.Stack(
                        gap=0,
                        children=[
                            dmc.Text("30D avg daily", size="xs", c=TEXT_LOW),
                            dmc.Text(fmt_vol(st.avg_volume_30d), size="lg", fw=700, c=TEXT_PRIMARY),
                        ],
                    ),
                    dmc.Stack(
                        gap=0,
                        children=[
                            dmc.Text("Latest", size="xs", c=TEXT_LOW),
                            dmc.Text(fmt_vol(st.latest_volume), size="lg", fw=700, c=TEXT_PRIMARY),
                        ],
                    ),
                ],
            ),
            dcc.Graph(
                figure=_volume_sparkline(snap),
                config={"displayModeBar": False},
                style={"height": 72},
                id="volume-sparkline",
            ),
        ],
        id="card-volume",
    )

    dd_txt = fmt_pct(st.drawdown_from_peak_pct, signed=True) if st.drawdown_from_peak_pct is not None else MDASH
    ath_txt = fmt_usd(st.ath_price) if st.ath_price is not None else MDASH
    h52 = fmt_usd(st.high_52w) if st.high_52w is not None else MDASH
    l52 = fmt_usd(st.low_52w) if st.low_52w is not None else MDASH

    range_card = _paper(
        [
            dmc.Text("Range & drawdown", size="sm", fw=600, c=TEXT_SECONDARY),
            dmc.SimpleGrid(
                cols={"base": 1, "sm": 2},
                spacing="sm",
                mt="xs",
                children=[
                    dmc.Stack(
                        gap=0,
                        children=[
                            dmc.Text("All-time high", size="xs", c=TEXT_LOW),
                            dmc.Text(ath_txt, fw=700, c=TEXT_PRIMARY),
                        ],
                    ),
                    dmc.Stack(
                        gap=0,
                        children=[
                            dmc.Text("Drawdown from peak", size="xs", c=TEXT_LOW),
                            dmc.Text(dd_txt, fw=700, c=TEXT_PRIMARY),
                        ],
                    ),
                    dmc.Stack(
                        gap=0,
                        children=[
                            dmc.Text("52-week high", size="xs", c=TEXT_LOW),
                            dmc.Text(h52, fw=700, c=TEXT_PRIMARY),
                        ],
                    ),
                    dmc.Stack(
                        gap=0,
                        children=[
                            dmc.Text("52-week low", size="xs", c=TEXT_LOW),
                            dmc.Text(l52, fw=700, c=TEXT_PRIMARY),
                        ],
                    ),
                ],
            ),
        ],
        id="card-range",
    )

    return html.Div(
        children=[
            html.Div(
                id="section-hero",
                className="mw-hero mw-fade-in",
                children=[
                    _paper(
                        [
                            dmc.Group(
                                align="flex-end",
                                justify="space-between",
                                children=[
                                    dmc.Stack(
                                        gap=4,
                                        children=[
                                            dmc.Text("BTC / USD", size="sm", tt="uppercase", c=TEXT_MUTED, fw=600),
                                            dmc.Title(
                                                fmt_usd(snap.latest_price),
                                                order=1,
                                                className="mw-hero-price mw-font-heading",
                                                c=TEXT_PRIMARY,
                                                id="hero-price",
                                            ),
                                            dmc.Group(
                                                gap="md",
                                                children=[
                                                    dmc.Text(
                                                        fmt_pct(chg, signed=True) if chg is not None else MDASH,
                                                        size="xl",
                                                        fw=600,
                                                        c=chg_color,
                                                        id="hero-change-pct",
                                                    ),
                                                    dmc.Text(
                                                        fmt_usd(snap.change_1d_abs) if snap.change_1d_abs is not None else MDASH,
                                                        size="lg",
                                                        c=TEXT_SECONDARY,
                                                        id="hero-change-abs",
                                                    ),
                                                ],
                                            ),
                                        ],
                                    ),
                                    dmc.Badge(snap.ma_summary_chip, variant="light", color="orange", size="lg", id="hero-ma-chip"),
                                ],
                            ),
                            dmc.Stack(gap=4, mt="md", children=hero_sub),
                        ],
                        className="mw-hero-card",
                    )
                ],
            ),
            html.Div(
                id="section-chart",
                className="mw-fade-in mw-delay-1",
                children=[
                    _paper(
                        [
                            dmc.Group(
                                justify="space-between",
                                mb="sm",
                                children=[
                                    dmc.Text("Price", fw=700, size="lg", c=TEXT_PRIMARY),
                                ],
                            ),
                            dmc.Text(range_note, size="xs", c=TEXT_LOW, mb="xs") if range_note else html.Div(),
                            dcc.Graph(
                                id="price-chart",
                                figure=fig,
                                config={"displayModeBar": False, "scrollZoom": False},
                                style={"height": 420},
                            ),
                        ],
                    )
                ],
            ),
            html.Div(
                id="section-stat-rail",
                className="mw-stat-rail mw-fade-in mw-delay-2",
                children=dmc.SimpleGrid(cols={"base": 2, "sm": 3, "lg": 6}, spacing="md", children=stat_cards),
            ),
            html.Div(
                id="section-supporting",
                className="mw-support-row mw-fade-in mw-delay-3",
                children=dmc.SimpleGrid(cols={"base": 1, "md": 2}, spacing="md", children=[vol_card, range_card]),
            ),
        ],
    )


def _stat_cell(label: str, value: str, hint: str) -> Any:
    return _paper(
        [
            dmc.Text(label, size="xs", tt="uppercase", c=TEXT_LOW, fw=600),
            dmc.Text(value, size="xl", fw=800, c=TEXT_PRIMARY, className="mw-stat-value"),
            dmc.Text(hint, size="xs", c=TEXT_MUTED),
        ],
        className="mw-stat-card",
    )


def _volume_sparkline(snap: BitcoinSnapshot) -> go.Figure:
    ch = snap.chart
    template = plotly_template()
    fig = go.Figure()
    fig.update_layout(template=template)
    if not ch.volume:
        fig.update_layout(margin={"l": 0, "r": 0, "t": 0, "b": 0})
        return fig
    fig.add_trace(
        go.Bar(
            x=list(range(len(ch.volume))),
            y=ch.volume,
            marker_color=ACCENT_SECONDARY,
            showlegend=False,
        )
    )
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    fig.update_layout(margin={"l": 0, "r": 0, "t": 0, "b": 0})
    return fig


def normalize_range_key(value: str | None, default: str) -> RangeKey:
    if value and value in RANGE_OPTIONS:
        return value  # type: ignore[return-value]
    if default in RANGE_OPTIONS:
        return default  # type: ignore[return-value]
    return "90D"


def render_page_root(
    history: pd.DataFrame,
    errors: list[str],
    range_key: RangeKey,
    client: BitcoinDataClient,
) -> tuple[Any, str, Any]:
    snap = client.build_snapshot(history, range_key)
    header_ts = MDASH
    if snap.as_of:
        header_ts = snap.as_of.strftime("%Y-%m-%d %H:%M UTC")
    if history.empty:
        return build_error_banner(errors), header_ts, build_empty_state()
    return build_error_banner(errors), header_ts, build_page_content(snap)


def run_dashboard_fetch(
    triggered_id: str | None,
    range_value: str | None,
    refresh_state: dict[str, int] | None,
    prior_store: dict[str, Any] | None,
    client: BitcoinDataClient,
    config: AppConfig,
) -> tuple[Any, str, dict[str, Any], Any]:
    """Banner, header timestamp, history store payload, page body."""
    prior_records = (prior_store or {}).get("records")
    default_r = config.dashboard.default_range
    rk = normalize_range_key(range_value, default_r)
    force_refresh = should_force_refresh(triggered_id, refresh_state)
    result = client.get_price_history(force_refresh=force_refresh)
    frame, err = coalesce_history(prior_records, result)
    store: dict[str, Any] = {
        "records": history_to_records(frame) if not frame.empty else [],
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }
    banner, header_ts, body = render_page_root(frame, err, rk, client)
    return banner, header_ts, store, body


def should_force_refresh(triggered_id: str | None, refresh_state: dict[str, int] | None) -> bool:
    return bool(triggered_id == "refresh-state" and refresh_state and refresh_state.get("refresh", 0) > 0)


def refresh_state_payload(n_clicks: int | None, current: dict[str, int] | None) -> dict[str, int]:
    return {"refresh": n_clicks or 0, "last": current.get("last") if current else 0}
