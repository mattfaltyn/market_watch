"""Data tables with optional link column."""

from __future__ import annotations

from typing import Callable

import dash_mantine_components as dmc
import pandas as pd
from dash import dcc, html

def _format_numeric(value: object, column: str) -> object:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "—"
    if isinstance(value, pd.Timestamp):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float)):
        if "return" in column.lower() or "spread" in column.lower() or "margin" in column.lower() or "growth" in column.lower() or column.lower() in {
            "base",
            "target",
            "actual",
            "gap",
            "delta",
            "score",
            "trend",
            "momentum",
            "volatility",
        }:
            return f"{value:+.1%}" if abs(value) <= 1.5 else f"{value:.2f}"
        if "days_to" in column.lower() or "count" in column.lower() or "alert" in column.lower():
            return f"{value:.0f}"
        if abs(value) >= 1000:
            return f"{value:,.2f}"
        return f"{value:.2f}"
    return value


def make_table(
    frame: pd.DataFrame,
    link_column: str | None = None,
    column_formatters: dict[str, Callable[[object], object]] | None = None,
    numeric_columns: list[str] | None = None,
) -> dmc.Paper | html.Div:
    if frame.empty:
        return html.Div("No rows.", className="empty-state")
    data = frame.copy()
    column_formatters = column_formatters or {}
    numeric_columns = numeric_columns or [column for column in data.columns if pd.api.types.is_numeric_dtype(data[column])]
    for column in data.columns:
        formatter = column_formatters.get(column)
        if formatter is not None:
            data[column] = data[column].map(formatter)
        else:
            data[column] = data[column].map(lambda value, c=column: _format_numeric(value, c))

    thead = html.Thead(html.Tr([html.Th(c) for c in data.columns]))
    rows = []
    for _, row in data.iterrows():
        cells = []
        for col in data.columns:
            val = row[col]
            if link_column and col == link_column and isinstance(val, str) and val.startswith("/"):
                cells.append(html.Td(dcc.Link("Open", href=val, className="table-link")))
            else:
                align = "right" if col in numeric_columns else "left"
                cells.append(html.Td(str(val), style={"textAlign": align}))
        rows.append(html.Tr(cells))
    tbody = html.Tbody(rows)
    return dmc.Paper(
        children=[html.Div(className="table-shell", children=[html.Table([thead, tbody], className="data-table")])],
        p="md",
        radius="lg",
        withBorder=True,
        className="data-table-panel",
    )
