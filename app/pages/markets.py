from __future__ import annotations

import pandas as pd
import dash_mantine_components as dmc
from dash import html

from app.components.charts import make_line_chart, yield_curve_bar
from app.components.ui import app_shell, badge, benchmark_card, heatstrip, section_panel, stat_chip
from app.config import AppConfig
from app.models import MarketSnapshot, RatesSnapshot


def render_markets(market: MarketSnapshot, rates: RatesSnapshot, sp500_history: pd.DataFrame, errors: list[str], config: AppConfig):
    benchmark_cards = [
        benchmark_card(
            index.symbol,
            f"{index.close:,.2f}" if index.close is not None else "Unavailable",
            f"1D {index.return_1d:+.1%} | 1M {index.return_1m:+.1%}"
            if index.return_1d is not None and index.return_1m is not None
            else "Insufficient history",
            "positive" if (index.return_1d or 0) >= 0 else "negative",
            source_note="via Yahoo Finance" if getattr(index, "source", None) == "yfinance" else None,
        )
        for index in market.indices
    ]

    ma_pills = []
    for index in market.indices[:4]:
        ma_pills.append(
            dmc.Group(
                [
                    dmc.Text(index.symbol, size="xs", fw=700),
                    dmc.Badge(f"20D {index.ma20_state}", size="xs", variant="light"),
                    dmc.Badge(f"50D {index.ma50_state}", size="xs", variant="light"),
                    dmc.Badge(f"200D {index.ma200_state}", size="xs", variant="light"),
                ],
                gap="xs",
            )
        )

    curve_labels = []
    curve_vals = []
    for label, val in [("2Y proxy", rates.y2), ("10Y", rates.y10), ("30Y", rates.y30)]:
        if val is not None:
            curve_labels.append(label)
            curve_vals.append(val)

    participation = dmc.Group(
        [
            dmc.RingProgress(
                sections=[{"value": market.positive_participation_ratio * 100, "color": "cyan"}],
                size=100,
                thickness=16,
                label=dmc.Text(f"{market.positive_participation_ratio:.0%}", size="lg", fw=700),
            ),
            dmc.Stack(
                [
                    dmc.Text("Participation", fw=600),
                    dmc.Text("Share of tracked names with positive 1M return", size="xs", c="dimmed"),
                    dmc.Text("50% reference: balanced breadth", size="xs", c="dimmed"),
                ],
                gap=4,
            ),
        ],
        align="center",
        gap="md",
    )

    indicator_labels = [index.symbol for index in market.indices]
    indicator_values = [index.return_1d or 0.0 for index in market.indices]

    rate_level_row = dmc.Group(
        [
            dmc.Tooltip(
                label="10Y Treasury yield (via Yahoo)",
                children=stat_chip("10Y", f"{rates.y10:.2%}" if rates.y10 is not None else "—", "rates"),
            ),
            dmc.Tooltip(
                label="10Y minus short-end proxy (^FVX 5Y stands in for 2Y); not a true 10Y–2Y spread.",
                children=stat_chip("10Y − 5Y proxy", f"{rates.spread_10y_short_proxy:+.2%}" if rates.spread_10y_short_proxy is not None else "—", "warning"),
            ),
            stat_chip("Short proxy (5Y)", f"{rates.y2:.2%}" if rates.y2 is not None else "—", "market"),
        ],
        gap="md",
    )

    delta_row = heatstrip(
        [
            (rates.change_10y_5d or 0.0) if rates.change_10y_5d is not None else None,
            (rates.change_10y_1m or 0.0) if rates.change_10y_1m is not None else None,
        ],
        ["10Y Δ 5D", "10Y Δ 1M"],
        value_format="yield",
    )

    sp500_chart = make_line_chart(
        sp500_history,
        "report_date",
        ["annual_returns"],
        "S&P 500 Annual Returns",
        semantic="market",
        x_axis_title="Date",
        y_axis_title="Return",
        range_selector=True,
    )

    children: list = []
    if ma_pills:
        children.append(dmc.Stack(ma_pills, gap="xs"))
    children.extend(
        [
            section_panel("Benchmark Tape", [html.Div(className="chart-wall", children=benchmark_cards)], subtitle="Configured market-watch symbols"),
            html.Div(
                className="two-col",
                children=[
                    section_panel(
                        "Rates",
                        [rate_level_row, dmc.Text("Yield changes (10Y)", size="xs", c="dimmed", mt="sm"), delta_row],
                        subtitle="Levels vs changes",
                    ),
                    section_panel(
                        "Breadth",
                        [heatstrip(indicator_values, indicator_labels, value_format="percent"), participation],
                        subtitle="1D moves and participation",
                    ),
                ],
            ),
        ]
    )
    if curve_labels:
        children.append(
            section_panel(
                "Yield curve (snapshot)",
                [yield_curve_bar(curve_labels, curve_vals, "Treasury proxies")],
                subtitle="Yahoo Finance proxies; short end uses ^FVX",
            )
        )
    children.append(section_panel("S&P 500 context", [sp500_chart], subtitle="Annual return series (supporting)"))

    return app_shell(
        children,
        page_title="Secondary macro telemetry feeding KISS.",
        active_page="markets",
        status_meta={"as_of": market.as_of or rates.as_of, "scope": "Support data"},
        warnings=errors,
    )
