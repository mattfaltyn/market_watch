from __future__ import annotations

from dash import html
import pandas as pd

from app.components.ui import app_shell, error_box, make_table, metric_card
from app.models import MetricCard


def render_watchlist(snapshot: pd.DataFrame, errors: list[str]):
    display = snapshot.copy()
    if not display.empty:
        display["detail"] = display["symbol"].apply(lambda symbol: f"/ticker/{symbol}")
        display["alerts"] = display["alerts"].apply(lambda items: " · ".join(items[:3]) if isinstance(items, list) and items else "—")

    cards = [
        MetricCard("Tracked Symbols", str(len(snapshot.index)), "Configured watchlist", "neutral", "compact"),
        MetricCard("Upcoming Earnings", str(int((snapshot.get("days_to_earnings", pd.Series(dtype=float)).fillna(999) <= 14).sum())) if not snapshot.empty else "0", "Within next 14 days", "warning", "compact"),
        MetricCard("Avg 1D Move", f"{snapshot['return_1d'].dropna().mean():+.2%}" if not snapshot.empty and "return_1d" in snapshot.columns and snapshot["return_1d"].notna().any() else "Unavailable", "Across tracked names", "market", "compact"),
        MetricCard("High Severity Alerts", str(int(snapshot.get("high_alert_count", pd.Series(dtype=int)).fillna(0).sum())) if not snapshot.empty else "0", "Immediate review required", "negative", "compact"),
    ]

    return app_shell(
        [
            error_box(errors),
            html.Div(className="kpi-strip", children=[metric_card(card) for card in cards]),
            html.Div(className="section", children=[
                html.Div(className="section-heading", children=[
                    html.H2("Watchlist Snapshot"),
                    html.P("Sort for event risk, valuation stretch, and short-term price pressure."),
                ]),
                make_table(
                    display[
                        [
                            "symbol",
                            "close",
                            "return_1d",
                            "return_5d",
                            "return_1m",
                            "beta_1y",
                            "days_to_earnings",
                            "ttm_pe",
                            "industry_ttm_pe",
                            "recent_news_7d",
                            "filing_count_30d",
                            "alert_count",
                            "alerts",
                            "detail",
                        ]
                    ]
                    if not display.empty
                    else display,
                    numeric_columns=["close", "return_1d", "return_5d", "return_1m", "beta_1y", "days_to_earnings", "ttm_pe", "industry_ttm_pe", "recent_news_7d", "filing_count_30d", "alert_count"],
                ),
            ]),
        ],
        page_title="Sortable watchlist view for signals, valuation, and catalysts.",
        active_page="watchlist",
        status_meta={"scope": f"{len(snapshot.index)} tracked symbols"},
    )
