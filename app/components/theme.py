"""Mantine theme tokens and shared Plotly styling."""

from __future__ import annotations

import plotly.graph_objects as go

SURFACE_BG = "#071018"
SURFACE_SHELL = "#0d1823"
SURFACE_PANEL = "#111f2d"
SURFACE_INSET = "#162737"
SURFACE_STRONG = "#1c3143"
TEXT_PRIMARY = "#f3f7fb"
TEXT_SECONDARY = "#a8b6c5"
TEXT_MUTED = "#7f90a3"
BORDER_SUBTLE = "rgba(140, 164, 191, 0.18)"
BORDER_STRONG = "rgba(140, 164, 191, 0.28)"

# Semantic colors aligned across UI and charts
COLOR_MAP: dict[str, str] = {
    "positive": "#3fd07a",
    "negative": "#ff6b6b",
    "warning": "#f6b55f",
    "neutral": "#93a6bc",
    "market": "#45b7d9",
    "rates": "#d59b4d",
    "bullish": "#3fd07a",
    "neutral_state": "#93a6bc",
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
    "fontFamily": "'IBM Plex Sans', 'Avenir Next', sans-serif",
    "headings": {"fontFamily": "'IBM Plex Sans Condensed', 'IBM Plex Sans', sans-serif"},
    "primaryColor": "cyan",
    "primaryShade": 6,
    "defaultRadius": "md",
    "colors": {
        "dark": [
            "#d8e1ea",
            "#b5c1cd",
            "#8ea0b0",
            "#6f8598",
            "#4a6072",
            "#2b3d4f",
            "#1c2a38",
            "#15212d",
            "#0d1823",
            "#071018",
        ]
    },
    "components": {
        "Paper": {
            "defaultProps": {"withBorder": True, "radius": "lg", "bg": SURFACE_PANEL},
        },
        "Badge": {"defaultProps": {"radius": "xl"}},
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
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor=SURFACE_PANEL,
            font={"color": TEXT_PRIMARY, "family": "'IBM Plex Sans', sans-serif"},
            colorway=SERIES_PALETTE,
            legend={
                "font": {"color": TEXT_SECONDARY},
                "bgcolor": "rgba(0,0,0,0)",
                "borderwidth": 0,
            },
            xaxis={
                "gridcolor": "rgba(140,164,191,0.10)",
                "zerolinecolor": "rgba(140,164,191,0.16)",
                "linecolor": "rgba(140,164,191,0.22)",
                "tickfont": {"color": TEXT_MUTED},
                "title": {"font": {"color": TEXT_MUTED, "size": 12}},
            },
            yaxis={
                "gridcolor": "rgba(140,164,191,0.10)",
                "zerolinecolor": "rgba(140,164,191,0.16)",
                "linecolor": "rgba(140,164,191,0.22)",
                "tickfont": {"color": TEXT_MUTED},
                "title": {"font": {"color": TEXT_MUTED, "size": 12}},
            },
            title={"font": {"color": TEXT_PRIMARY, "size": 14}},
            hoverlabel={"bgcolor": SURFACE_INSET, "font": {"color": TEXT_PRIMARY}},
        )
    )
    return _PLOTLY_TEMPLATE
