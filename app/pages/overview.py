from __future__ import annotations

from dash import html
import pandas as pd

from app.components.ui import app_shell, benchmark_card, error_box, insight_list, make_line_chart, metric_card
from app.models import MetricCard
from app.services.signals import summarize_alerts


def render_overview(market, rates, regime, watchlist_frame: pd.DataFrame, sp500_history: pd.DataFrame, errors: list[str]):
    benchmark_cards = [
        benchmark_card(
            index.symbol,
            f"{index.close:,.2f}" if index.close is not None else "Unavailable",
            f"1D {index.return_1d:+.1%} | 1M {index.return_1m:+.1%}" if index.return_1d is not None and index.return_1m is not None else "Insufficient history",
            "positive" if (index.return_1d or 0) >= 0 else "negative",
        )
        for index in market.indices
    ]
    alert_summary = summarize_alerts(watchlist_frame)
    top_movers = watchlist_frame.sort_values("return_1d", ascending=False).head(5) if not watchlist_frame.empty and "return_1d" in watchlist_frame.columns else pd.DataFrame()
    brief_items = [
        regime.reasons[0] if regime.reasons else "Cross-asset conditions are mixed.",
        f"Positive 1M benchmark participation is {market.positive_participation_ratio:.0%}.",
        f"Watchlist high-severity alerts: {alert_summary['high_alerts']}.",
        f"Recent 7D watchlist news volume: {int(watchlist_frame.get('recent_news_7d', pd.Series(dtype=int)).fillna(0).sum()) if not watchlist_frame.empty else 0}.",
    ]
    mover_items = [f"{row.symbol} is {row.return_1d:+.1%} today with {row.alert_count:.0f} active alerts." for row in top_movers.itertuples()] if not top_movers.empty else ["No standout movers in the current watchlist snapshot."]
    cards = [
        MetricCard("Regime", regime.regime, f"Score {regime.score:+d}", "positive" if regime.regime == "Risk-On" else "negative" if regime.regime == "Risk-Off" else "warning", "kpi"),
        MetricCard("10Y Treasury", f"{rates.y10:.2%}" if rates.y10 is not None else "Unavailable", f"1M {rates.change_10y_1m:+.2%}" if rates.change_10y_1m is not None else "No recent change available", "rates", "kpi"),
        MetricCard("10Y-2Y Spread", f"{rates.spread_10y_2y:+.2%}" if rates.spread_10y_2y is not None else "Unavailable", "Yield curve shape", "market", "kpi"),
        MetricCard("Watchlist Alerts", str(alert_summary["total_alerts"]), f"{alert_summary['high_alerts']} high severity", "negative" if alert_summary["high_alerts"] else "neutral", "kpi"),
    ]

    return app_shell(
        [
            error_box(errors),
            html.Div(className="hero-grid", children=[
                html.Div(className="section hero-card tone-neutral", children=[
                    html.Div("Market Regime", className="hero-label"),
                    html.Div(regime.regime, className="hero-value"),
                    html.Div(", ".join(regime.reasons) if regime.reasons else "No strong cross-asset signal is dominating today.", className="hero-summary"),
                    html.Div(className="hero-footer", children=[
                        html.Span(f"Participation {market.positive_participation_ratio:.0%}", className="badge tone-neutral"),
                        html.Span(f"10Y {rates.y10:.2%}" if rates.y10 is not None else "10Y unavailable", className="badge tone-rates"),
                    ]),
                ]),
                html.Div(className="section briefing-card", children=[
                    html.H3("What changed today"),
                    html.Ul(className="briefing-list", children=[html.Li(item) for item in brief_items]),
                ]),
            ]),
            html.Div(className="kpi-strip", children=[metric_card(card) for card in cards]),
            html.Div(className="section-heading", children=[
                html.H2("Benchmark Tape"),
                html.P("A concise read on the major index complex."),
            ]),
            html.Div(className="market-tape", children=benchmark_cards),
            html.Div(className="info-grid", children=[
                html.Div(className="section", children=[make_line_chart(sp500_history, "report_date", ["annual_returns"], "S&P 500 Annual Returns", semantic="market")]),
                insight_list(mover_items, "Top Movers & Callouts"),
            ]),
        ],
        page_title="Broad market regime, rates, and high-level watchlist risk.",
        active_page="overview",
        status_meta={"as_of": market.as_of or rates.as_of, "scope": f"{len(market.indices)} benchmarks / {len(watchlist_frame.index)} watchlist names"},
    )
