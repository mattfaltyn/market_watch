from __future__ import annotations

from dash import html
import pandas as pd

from app.components.ui import app_shell, benchmark_card, error_box, insight_list, make_line_chart


def render_market_watch(market, rates, watchlist_frame: pd.DataFrame, sp500_history: pd.DataFrame, errors: list[str]):
    benchmark_cards = [
        benchmark_card(
            index.symbol,
            f"{index.close:,.2f}" if index.close is not None else "Unavailable",
            f"1D {index.return_1d:+.1%} | 1M {index.return_1m:+.1%}" if index.return_1d is not None and index.return_1m is not None else "Insufficient history",
            "positive" if (index.return_1d or 0) >= 0 else "negative",
        )
        for index in market.indices
    ]
    watch_items = [
        f"10Y Treasury {rates.y10:.2%}" if rates.y10 is not None else "10Y Treasury unavailable",
        f"10Y-2Y spread {rates.spread_10y_2y:+.2%}" if rates.spread_10y_2y is not None else "Curve unavailable",
        f"Tracked indicators: {len(watchlist_frame.index)}",
    ]
    return app_shell(
        [
            error_box(errors),
            html.Div(className="section-heading", children=[html.H2("Macro Dashboard"), html.P("Supporting context for the KISS engine.")]),
            html.Div(className="market-tape", children=benchmark_cards),
            html.Div(className="info-grid", children=[
                html.Div(className="section", children=[make_line_chart(sp500_history, "report_date", ["annual_returns"], "S&P 500 Annual Returns", semantic="market")]),
                insight_list(watch_items, "Market Watch"),
            ]),
        ],
        page_title="Secondary macro and market context feeding KISS.",
        active_page="market-watch",
        status_meta={"as_of": market.as_of or rates.as_of, "scope": "Support data"},
    )
