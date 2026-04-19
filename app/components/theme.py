"""Mantine theme tokens and shared Plotly styling."""

from __future__ import annotations

import plotly.graph_objects as go

# Semantic colors aligned across UI and charts
COLOR_MAP: dict[str, str] = {
    "positive": "#33d17a",
    "negative": "#ff6b6b",
    "warning": "#ffb347",
    "neutral": "#8aa4bf",
    "market": "#5bc0ff",
    "rates": "#ffb347",
    "bullish": "#33d17a",
    "neutral_state": "#8aa4bf",
    "bearish": "#ff6b6b",
}

SERIES_PALETTE: list[str] = [
    COLOR_MAP["market"],
    COLOR_MAP["positive"],
    COLOR_MAP["warning"],
    "#c084fc",
    COLOR_MAP["negative"],
    "#52d6ff",
]

SLEEVE_COLORS: dict[str, str] = {
    "SPY": "#4fb3ff",
    "AGG": "#8e8cf9",
    "BTC-USD": "#ff9f43",
    "USFR": "#39d98a",
    "QQQ": "#52d6ff",
    "IWM": "#c084fc",
    "DIA": "#f7c56b",
    "GLD": "#ffd166",
    "USO": "#ff7f50",
    "DBC": "#58d68d",
}

THEME: dict = {
    "colorScheme": "dark",
    "fontFamily": "'IBM Plex Sans', 'Inter', 'Avenir Next', sans-serif",
    "primaryColor": "cyan",
    "defaultRadius": "md",
    "components": {
        "Paper": {"defaultProps": {"withBorder": True, "radius": "lg"}},
    },
}

_PLOTLY_TEMPLATE: go.layout.Template | None = None


def series_color(index: int, semantic: str | None = None) -> str:
    if semantic:
        return COLOR_MAP.get(semantic, COLOR_MAP["neutral"])
    return SERIES_PALETTE[index % len(SERIES_PALETTE)]


def plotly_template() -> go.layout.Template:
    global _PLOTLY_TEMPLATE
    if _PLOTLY_TEMPLATE is not None:
        return _PLOTLY_TEMPLATE
    _PLOTLY_TEMPLATE = go.layout.Template(
        layout=go.Layout(
            paper_bgcolor="rgba(7,17,26,0)",
            plot_bgcolor="rgba(7,17,26,0)",
            font={"color": "#e6f1ff", "family": "'IBM Plex Sans', sans-serif"},
            xaxis={
                "gridcolor": "rgba(140,163,186,0.14)",
                "zerolinecolor": "rgba(140,163,186,0.35)",
                "linecolor": "#7f96ad",
                "tickfont": {"color": "#7f96ad"},
            },
            yaxis={
                "gridcolor": "rgba(140,163,186,0.14)",
                "zerolinecolor": "rgba(140,163,186,0.45)",
                "linecolor": "#7f96ad",
                "tickfont": {"color": "#7f96ad"},
            },
            hoverlabel={"bgcolor": "#0d1b29", "font": {"color": "#e6f1ff"}},
        )
    )
    return _PLOTLY_TEMPLATE
