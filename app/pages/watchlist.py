from __future__ import annotations

import dash_mantine_components as dmc
import pandas as pd
from dash import html

from app.components.tables import make_table
from app.components.ui import app_shell, metric_card
from app.config import AppConfig
from app.models import MetricCard


def render_watchlist(snapshot: pd.DataFrame, errors: list[str], config: AppConfig):
    display = snapshot.copy()
    if not display.empty:
        display["detail"] = display["symbol"].apply(lambda symbol: f"/ticker/{symbol}")
        display["alerts"] = display["alerts"].apply(lambda items: " · ".join(items[:3]) if isinstance(items, list) and items else "—")

    cards = [
        MetricCard("Tracked Symbols", str(len(snapshot.index)), "Configured watchlist", "neutral", "compact"),
        MetricCard(
            "Upcoming Earnings",
            str(int((snapshot.get("days_to_earnings", pd.Series(dtype=float)).fillna(999) <= 14).sum())) if not snapshot.empty else "0",
            "Within next 14 days",
            "warning",
            "compact",
        ),
        MetricCard(
            "Avg 1D Move",
            f"{snapshot['return_1d'].dropna().mean():+.2%}"
            if not snapshot.empty and "return_1d" in snapshot.columns and snapshot["return_1d"].notna().any()
            else "Unavailable",
            "Across tracked names",
            "market",
            "compact",
        ),
        MetricCard(
            "High Severity Alerts",
            str(int(snapshot.get("high_alert_count", pd.Series(dtype=int)).fillna(0).sum())) if not snapshot.empty else "0",
            "Immediate review required",
            "negative",
            "compact",
        ),
    ]

    table_cols = [
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
        "alert_count",
        "alerts",
        "detail",
    ]
    table_body = display[table_cols] if not display.empty and all(c in display.columns for c in table_cols) else display

    body = [
        dmc.SimpleGrid([metric_card(card) for card in cards], cols={"base": 1, "sm": 2, "lg": 4}, spacing="md"),
        dmc.Title("Watchlist Snapshot", order=3, mt="lg"),
        dmc.Text("Sort for event risk, valuation stretch, and short-term price pressure.", size="sm", c="dimmed", mb="sm"),
        make_table(
            table_body,
            link_column="detail",
            numeric_columns=["close", "return_1d", "return_5d", "return_1m", "beta_1y", "days_to_earnings", "ttm_pe", "industry_ttm_pe", "recent_news_7d", "alert_count"],
        )
        if not display.empty
        else dmc.Text("No symbols configured in settings.", c="dimmed"),
    ]

    return app_shell(
        body,
        page_title="Sortable watchlist view for signals, valuation, and catalysts.",
        active_page="watchlist",
        status_meta={"as_of": None, "scope": f"{len(snapshot.index)} symbols", "source": "yfinance"},
        warnings=errors,
    )
