from __future__ import annotations

import pandas as pd
from dash import html

from app.components.ui import (
    alert_list,
    app_shell,
    badge,
    error_box,
    feed_panel,
    make_bar_chart,
    make_line_chart,
    make_table,
    section_panel,
    signal_meter,
    stat_chip,
)
from app.models import TickerDetailBundle


def _latest_metric(frame: pd.DataFrame, column: str) -> float | None:
    if frame.empty or column not in frame.columns:
        return None
    series = pd.to_numeric(frame[column], errors="coerce").dropna()
    if series.empty:
        return None
    return float(series.iloc[-1])


def _mini_stat(label: str, value: float | None) -> html.Div:
    display = "—" if value is None else f"{value:+.1%}" if abs(value) <= 1.0 else f"{value:.2f}"
    return html.Div(className="mini-stat", children=[html.Div(label, className="mini-stat-label"), html.Div(display, className="mini-stat-value")])


def render_ticker_detail(bundle: TickerDetailBundle):
    info = bundle.info.iloc[0].to_dict() if not bundle.info.empty else {}
    company_name = str(info.get("long_name", info.get("company_name", bundle.symbol)))
    pe_frame = bundle.valuation.get("ttm_pe", pd.DataFrame())
    roe = _latest_metric(bundle.quality.get("roe", pd.DataFrame()), "roe")
    roic = _latest_metric(bundle.quality.get("roic", pd.DataFrame()), "roic")
    revenue_growth = _latest_metric(bundle.growth.get("revenue_yoy_growth", pd.DataFrame()), "revenue_yoy_growth")
    eps_growth = _latest_metric(bundle.growth.get("eps_yoy_growth", pd.DataFrame()), "eps_yoy_growth")
    alert_tone = "negative" if any(flag.severity == "high" for flag in bundle.alerts) else "warning" if bundle.alerts else "positive"

    quality_panel = html.Div(
        className="section-metric-grid",
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
                className="ticker-header",
                children=[
                    section_panel(
                        "Ticker Header",
                        [
                            html.Div(bundle.symbol, className="ticker-symbol"),
                            html.Div(company_name, className="ticker-company"),
                            html.Div(
                                className="meta-row",
                                children=[
                                    badge(str(info.get("sector", "Sector unavailable")), "market"),
                                    badge(str(info.get("industry", "Industry unavailable")), "neutral"),
                                    badge(f"{len(bundle.alerts)} alerts", alert_tone),
                                ],
                            ),
                        ],
                        subtitle="Company context",
                    ),
                    alert_list(bundle.alerts, title="Alert Panel"),
                ],
            ),
            html.Div(
                className="three-col",
                children=[
                    section_panel("Price", [make_line_chart(bundle.price, "report_date", ["close"], f"{bundle.symbol} Price", semantic="market")], subtitle="Primary trend"),
                    section_panel("Valuation", [make_line_chart(pe_frame, "report_date", ["ttm_pe"], "TTM P/E", semantic="warning")], subtitle="Primary valuation"),
                    section_panel(
                        "Quality / Growth",
                        [
                            quality_panel,
                            signal_meter(roe or 0.0, -0.5, 0.5, "ROE", "positive" if (roe or 0.0) >= 0 else "negative"),
                            signal_meter(revenue_growth or 0.0, -1.0, 1.0, "Revenue", "positive" if (revenue_growth or 0.0) >= 0 else "negative"),
                        ],
                        subtitle="Mini metric stack",
                    ),
                ],
            ),
            html.Div(
                className="two-col",
                children=[
                    feed_panel("News Feed", bundle.news, "title", ["publish_time", "publisher", "source"]),
                    feed_panel("Filing Feed", bundle.filings, "form_type", ["filing_date", "report_date"]),
                ],
            ),
            html.Div(
                className="two-col",
                children=[
                    section_panel("Segment Mix", [make_bar_chart(bundle.revenue_breakdown.get("segment", pd.DataFrame()), "report_date", "Latest Segment Mix", semantic="market")]),
                    section_panel("Geography Mix", [make_bar_chart(bundle.revenue_breakdown.get("geography", pd.DataFrame()), "report_date", "Latest Geographic Mix", semantic="market")]),
                ],
            ),
            section_panel("Transcript Grid", [make_table(bundle.transcripts.head(20))], subtitle="Availability and dates"),
        ],
        page_title=f"{bundle.symbol} visual intelligence panel.",
        active_page="ticker",
        status_meta={"scope": bundle.symbol},
    )
