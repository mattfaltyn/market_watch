from __future__ import annotations

from dash import html
import pandas as pd

from app.components.ui import (
    app_shell,
    badge,
    benchmark_card,
    error_box,
    heatstrip,
    make_line_chart,
    section_panel,
    stat_chip,
)


def render_market_watch(market, rates, watchlist_frame: pd.DataFrame, sp500_history: pd.DataFrame, errors: list[str]):
    benchmark_cards = [
        benchmark_card(
            index.symbol,
            f"{index.close:,.2f}" if index.close is not None else "Unavailable",
            f"1D {index.return_1d:+.1%} | 1M {index.return_1m:+.1%}" if index.return_1d is not None and index.return_1m is not None else "Insufficient history",
            "positive" if (index.return_1d or 0) >= 0 else "negative",
            source_note="via Yahoo Finance" if getattr(index, "source", None) == "yfinance" else None,
        )
        for index in market.indices
    ]
    rate_values = [
        rates.y10 or 0.0,
        rates.spread_10y_2y or 0.0,
        rates.change_10y_5d or 0.0,
        rates.change_10y_1m or 0.0,
    ]
    indicator_labels = [index.symbol for index in market.indices]
    indicator_values = [index.return_1d or 0.0 for index in market.indices]
    return app_shell(
        [
            error_box(errors),
            section_panel("Benchmark Tape", [html.Div(className="chart-wall", children=benchmark_cards)], subtitle="Secondary telemetry"),
            html.Div(
                className="two-col",
                children=[
                    section_panel(
                        "Rates Module",
                        [
                            html.Div(
                                className="chip-row",
                                children=[
                                    stat_chip("10Y", f"{rates.y10:.2%}" if rates.y10 is not None else "—", "rates"),
                                    stat_chip("10Y-2Y", f"{rates.spread_10y_2y:+.2%}" if rates.spread_10y_2y is not None else "—", "warning"),
                                    stat_chip("5D", f"{rates.change_10y_5d:+.2%}" if rates.change_10y_5d is not None else "—", "market"),
                                    stat_chip("1M", f"{rates.change_10y_1m:+.2%}" if rates.change_10y_1m is not None else "—", "market"),
                                ],
                            ),
                            heatstrip(rate_values, ["10Y", "CURVE", "5D", "1M"], value_format="yield"),
                        ],
                        subtitle="Rate pressure",
                    ),
                    section_panel(
                        "Indicator Strip",
                        [
                            heatstrip(indicator_values, indicator_labels, value_format="percent"),
                            html.Div(className="chip-row", children=[badge(f"{len(market.indices)} tracked", "market"), badge(f"{market.positive_participation_ratio:.0%} positive", "positive")]),
                        ],
                        subtitle="Configured market-watch symbols",
                    ),
                ],
            ),
            section_panel(
                "Macro Chart Wall",
                [
                    html.Div(
                        className="two-col",
                        children=[
                            make_line_chart(sp500_history, "report_date", ["annual_returns"], "S&P 500 Annual Returns", semantic="market"),
                            make_line_chart(sp500_history, "report_date", ["annual_returns"], "Risk Context", semantic="rates"),
                        ],
                    )
                ],
                subtitle="Supporting context for KISS",
            ),
        ],
        page_title="Secondary macro telemetry feeding KISS.",
        active_page="market-watch",
        status_meta={"as_of": market.as_of or rates.as_of, "scope": "Support data"},
    )
