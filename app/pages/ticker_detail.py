from __future__ import annotations

from dash import html

from app.components.ui import alert_list, app_shell, badge, error_box, feed_panel, make_bar_chart, make_line_chart, make_table, metric_card
from app.models import MetricCard, TickerDetailBundle


def render_ticker_detail(bundle: TickerDetailBundle):
    info = bundle.info.iloc[0].to_dict() if not bundle.info.empty else {}
    company_name = str(info.get("long_name", info.get("company_name", bundle.symbol)))
    cards = [
        MetricCard("Symbol", bundle.symbol, variant="compact"),
        MetricCard("Sector", str(info.get("sector", "Unavailable")), variant="compact"),
        MetricCard("Industry", str(info.get("industry", "Unavailable")), variant="compact"),
    ]

    return app_shell(
        [
            error_box(bundle.errors),
            html.Div(className="ticker-header", children=[
                html.Div(className="section ticker-summary", children=[
                    html.Div(bundle.symbol, className="ticker-symbol"),
                    html.Div(company_name, className="ticker-company"),
                    html.Div(className="meta-row", children=[
                        badge(str(info.get("sector", "Sector unavailable")), "market"),
                        badge(str(info.get("industry", "Industry unavailable")), "neutral"),
                    ]),
                    html.Div(className="card-grid", children=[metric_card(card) for card in cards]),
                ]),
                html.Div(className="section", children=[alert_list(bundle.alerts)]),
            ]),
            html.Div(className="three-col", children=[
                html.Div(className="section", children=[make_line_chart(bundle.price, "report_date", ["close"], f"{bundle.symbol} Price", semantic="market")]),
                html.Div(className="section", children=[make_line_chart(bundle.valuation.get("ttm_pe", bundle.price), "report_date", ["ttm_pe"], "TTM P/E", semantic="warning")]),
                html.Div(className="section", children=[alert_list(bundle.alerts)]),
            ]),
            html.Div(className="two-col", children=[
                feed_panel("News", bundle.news, "title", ["publish_time", "publisher", "source"]),
                feed_panel("Filings", bundle.filings, "form_type", ["filing_date", "report_date"]),
            ]),
            html.Div(className="two-col", children=[
                html.Div(className="section", children=[html.H3("Revenue by Segment"), make_bar_chart(bundle.revenue_breakdown.get("segment"), "report_date", "Latest Segment Mix", semantic="market")]),
                html.Div(className="section", children=[html.H3("Revenue by Geography"), make_bar_chart(bundle.revenue_breakdown.get("geography"), "report_date", "Latest Geographic Mix", semantic="market")]),
            ]),
            html.Div(className="section", children=[html.H3("Transcript Availability"), make_table(bundle.transcripts.head(20))]),
        ],
        page_title=f"{bundle.symbol} detail view for price, fundamentals, news, and filings.",
        active_page="watchlist",
        status_meta={"scope": bundle.symbol},
    )
