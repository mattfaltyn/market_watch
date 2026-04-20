"""Mantine theme and Plotly colors aligned with assets/theme.css tokens."""

from __future__ import annotations

import plotly.graph_objects as go

BG_PRIMARY = "#1E1E44"
BG_DEEP = "#0F0F20"
BG_SECONDARY = "#171733"
SURFACE_DARK = "#3F3C59"
ACCENT_PRIMARY = "#FC9841"
ACCENT_SECONDARY = "#6DA9E4"
TEXT_PRIMARY = "#FDFDFD"
TEXT_SECONDARY = "#BFBFC8"
TEXT_MUTED = "#898BA0"
TEXT_LOW = "#676174"
MOVE_UP = "#6DA9E4"
MOVE_DOWN = "#9A7A8A"

THEME: dict = {
    "colorScheme": "dark",
    "fontFamily": "Manrope, system-ui, sans-serif",
    "headings": {"fontFamily": "'Space Grotesk', Manrope, system-ui, sans-serif"},
    "primaryColor": "orange",
    "primaryShade": 6,
    "defaultRadius": "lg",
    "colors": {
        "orange": [
            "#fff4e8",
            "#fde4cc",
            "#fbc896",
            "#f8ad66",
            "#f5953f",
            "#FC9841",
            "#e88935",
            "#c4712a",
            "#9e5a22",
            "#7a461a",
        ],
        "dark": [
            TEXT_PRIMARY,
            TEXT_SECONDARY,
            TEXT_MUTED,
            "#5a5c70",
            SURFACE_DARK,
            "#353350",
            BG_SECONDARY,
            "#1a1a38",
            BG_DEEP,
            BG_PRIMARY,
        ],
    },
    "components": {
        "Paper": {
            "defaultProps": {"withBorder": True, "radius": "lg", "shadow": "sm"},
        },
        "Button": {"defaultProps": {"radius": "md"}},
    },
}

_PLOTLY_TEMPLATE: go.layout.Template | None = None


def plotly_template() -> go.layout.Template:
    global _PLOTLY_TEMPLATE
    if _PLOTLY_TEMPLATE is not None:
        return _PLOTLY_TEMPLATE
    _PLOTLY_TEMPLATE = go.layout.Template(
        layout=go.Layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font={"color": TEXT_MUTED, "family": "Manrope, system-ui, sans-serif"},
            colorway=[ACCENT_PRIMARY, ACCENT_SECONDARY],
            showlegend=False,
            margin={"l": 48, "r": 16, "t": 8, "b": 40},
            legend={
                "font": {"color": TEXT_MUTED, "size": 11},
                "bgcolor": "rgba(0,0,0,0)",
                "borderwidth": 0,
            },
            xaxis={
                "gridcolor": "rgba(63,60,89,0.35)",
                "zeroline": False,
                "linecolor": "rgba(103,97,116,0.4)",
                "tickfont": {"color": TEXT_LOW, "size": 10},
            },
            yaxis={
                "gridcolor": "rgba(63,60,89,0.35)",
                "zeroline": False,
                "linecolor": "rgba(103,97,116,0.4)",
                "tickfont": {"color": TEXT_LOW, "size": 10},
                "tickprefix": "$",
            },
            hoverlabel={
                "bgcolor": SURFACE_DARK,
                "font": {"color": TEXT_PRIMARY, "family": "Manrope, system-ui, sans-serif"},
                "bordercolor": "rgba(252,152,65,0.35)",
            },
        )
    )
    return _PLOTLY_TEMPLATE
