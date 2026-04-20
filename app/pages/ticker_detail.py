from __future__ import annotations

import pandas as pd
import dash_mantine_components as dmc
from dash import dcc, html

from app.components.charts import make_line_chart, price_with_mas
from app.components.ui import app_shell, badge, error_box, section_panel
from app.config import AppConfig
from app.models import TickerDetailBundle


def _latest_metric(frame: pd.DataFrame, column: str) -> float | None:
    if frame.empty or column not in frame.columns:
        return None
    series = pd.to_numeric(frame[column], errors="coerce").dropna()
    if series.empty:
        return None
    return float(series.iloc[-1])


def _mini_stat(label: str, value: float | None, *, as_percent: bool = True) -> html.Div:
    if value is None:
        display = "—"
    elif as_percent:
        display = f"{value:.1%}" if abs(value) <= 2.0 else f"{value:.2f}"
    else:
        display = f"{value:.2f}"
    return html.Div(className="mini-stat", children=[html.Div(label, className="mini-stat-label"), html.Div(display, className="mini-stat-value")])


def render_ticker_detail(bundle: TickerDetailBundle, config: AppConfig):
    info = bundle.info.iloc[0].to_dict() if not bundle.info.empty else {}
    company_name = str(info.get("long_name", info.get("company_name", bundle.symbol)))
    pe_frame = bundle.valuation.get("ttm_pe", pd.DataFrame())
    industry_pe = bundle.valuation.get("industry_ttm_pe", pd.DataFrame())
    ind_col = "industry_ttm_pe" if not industry_pe.empty and "industry_ttm_pe" in industry_pe.columns else "ttm_pe"
    ind_latest = _latest_metric(industry_pe, ind_col) if not industry_pe.empty else None

    roe = _latest_metric(bundle.quality.get("roe", pd.DataFrame()), "roe")
    roic = _latest_metric(bundle.quality.get("roic", pd.DataFrame()), "roic")
    revenue_growth = _latest_metric(bundle.growth.get("revenue_yoy_growth", pd.DataFrame()), "revenue_yoy_growth")
    eps_growth = _latest_metric(bundle.growth.get("eps_yoy_growth", pd.DataFrame()), "eps_yoy_growth")
    alert_tone = "negative" if any(flag.severity == "high" for flag in bundle.alerts) else "warning" if bundle.alerts else "positive"

    windows = config.chart_windows
    short = int(windows.get("short_days", 20))
    med = int(windows.get("medium_days", 50))
    long = int(windows.get("long_days", 200))
    ma_windows = {f"{short}D": short, f"{med}D": med, f"{long}D": long}

    vol_col = None
    if not bundle.price.empty:
        for col in ("volume", "Volume"):
            if col in bundle.price.columns:
                vol_col = col
                break
    price_chart = price_with_mas(bundle.price, bundle.symbol, ma_windows, volume_column=vol_col)

    pe_chart = make_line_chart(
        pe_frame,
        "report_date",
        ["ttm_pe"],
        "TTM P/E",
        semantic="warning",
        x_axis_title="Date",
        y_axis_title="P/E",
        extra_hlines=[(ind_latest, "Industry median")] if ind_latest is not None else None,
        range_selector=True,
    )

    quality_panel = html.Div(
        className="mini-stat-grid section-metric-grid",
        children=[
            _mini_stat("ROE", roe),
            _mini_stat("ROIC", roic),
            _mini_stat("Revenue YoY", revenue_growth),
            _mini_stat("EPS YoY", eps_growth),
        ],
    )

    news_items = []
    if not bundle.news.empty and "title" in bundle.news.columns:
        for row in bundle.news.head(8).to_dict("records"):
            news_items.append(
                dmc.TimelineItem(
                    title=str(row.get("title", "")),
                    children=dmc.Text(
                        " • ".join(
                            str(row.get(c, ""))
                            for c in ("publish_time", "publisher", "source")
                            if row.get(c) not in (None, "", pd.NaT)
                        ),
                        size="xs",
                        c="dimmed",
                    ),
                )
            )
    news_block = dmc.Timeline(news_items, active=-1, bulletSize=8, lineWidth=1) if news_items else dmc.Text("No news", c="dimmed")

    alert_blocks = [
        dmc.Alert(
            title=flag.severity.upper(),
            color="red" if flag.severity == "high" else "yellow" if flag.severity == "medium" else "blue",
            children=[
                dmc.Group(
                    [
                        dmc.Text(flag.message),
                        dmc.Tooltip(
                            label="Heuristic from configured thresholds (large moves, valuation vs industry, curve).",
                            children=dmc.Badge("?", size="xs", circle=True),
                        ),
                    ],
                    gap="sm",
                )
            ],
        )
        for flag in bundle.alerts
    ]

    yahoo_url = f"https://finance.yahoo.com/quote/{bundle.symbol}"
    header_stats = html.Div(
        className="hero-detail-row",
        children=[
            _mini_stat("ROE", roe),
            _mini_stat("ROIC", roic),
            _mini_stat("Revenue YoY", revenue_growth),
            _mini_stat("EPS YoY", eps_growth),
        ],
    )

    return app_shell(
        [
            error_box(bundle.errors),
            html.Div(
                className="detail-header ticker-header",
                children=[
                    section_panel(
                        "Ticker Header",
                        [
                            html.Div(
                                className="ticker-title-block",
                                children=[
                                    html.Div(bundle.symbol, className="ticker-symbol"),
                                    html.Div(company_name, className="ticker-company"),
                                ],
                            ),
                            html.Div(
                                className="meta-row",
                                children=[
                                    badge(bundle.role_label or "Indicator", "positive"),
                                    badge(str(info.get("sector", "Sector unavailable")), "market"),
                                    badge(str(info.get("industry", "Industry unavailable")), "neutral"),
                                    badge(f"{len(bundle.alerts)} alerts", alert_tone),
                                    dcc.Link("Yahoo Finance", href=yahoo_url, target="_blank"),
                                ],
                            ),
                            header_stats,
                        ],
                        subtitle="Company context",
                        header_right=badge(bundle.symbol, "market"),
                        variant="shell",
                        density="compact",
                    ),
                    section_panel(
                        "Alert Panel",
                        [dmc.Stack(alert_blocks, gap="sm")] if alert_blocks else [html.Div("No active alerts for this symbol.", className="empty-state")],
                        subtitle="Threshold-driven warnings and review cues",
                        header_right=badge(f"{len(bundle.alerts)} active", alert_tone),
                        variant="inset",
                        density="compact",
                    ),
                ],
            ),
            html.Div(
                className="chart-band three-col",
                children=[
                    section_panel("Price", [price_chart], subtitle="Close with moving averages from settings", density="compact"),
                    section_panel("Valuation", [pe_chart], subtitle="TTM P/E vs industry median line when available", density="compact"),
                    section_panel("Quality / Growth", [quality_panel], subtitle="Latest fundamentals", density="compact"),
                ],
            ),
            section_panel("News", [news_block], subtitle="Recent headlines", header_right=badge("Recent", "market"), density="compact"),
        ],
        page_title=f"{bundle.symbol} regime intelligence panel.",
        active_page="ticker",
        status_meta={"as_of": bundle.as_of, "scope": bundle.symbol, "source": "yfinance"},
    )
