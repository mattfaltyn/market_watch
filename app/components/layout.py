"""App shell and top-level layout."""

from __future__ import annotations

import dash_mantine_components as dmc
from dash import dcc, html

from app.components.primitives import error_box, format_timestamp, normalize_status_meta, section_panel


def _nav_link(label: str, href: str, active: bool) -> dcc.Link:
    return dcc.Link(
        dmc.Button(label, variant="filled" if active else "light", color="cyan", size="sm", radius="xl"),
        href=href,
        style={"textDecoration": "none"},
    )


def app_shell(
    children,
    page_title: str,
    active_page: str = "overview",
    status_meta: dict | None = None,
    *,
    warnings: list[str] | None = None,
    errors: list[str] | None = None,
) -> html.Div:
    """Top shell with Overview / Markets / Watchlist nav and status strip."""
    status_meta = normalize_status_meta(status_meta)
    nav = [
        ("Overview", "/", "overview"),
        ("Markets", "/markets", "markets"),
        ("Watchlist", "/watchlist", "watchlist"),
    ]
    nav_row = dmc.Group(
        [_nav_link(label, href, active_page == key) for label, href, key in nav],
        gap="sm",
    )
    frame = dmc.Stack(
        [
            dmc.Group(
                [
                    dmc.Stack(
                        [
                            dmc.Text("KISS / MARKET REGIME", size="xs", c="cyan.4", tt="uppercase", style={"letterSpacing": "0.16em"}),
                            dmc.Title("KISS Terminal", order=1, style={"margin": 0}),
                            dmc.Text(page_title, size="sm", c="dimmed"),
                        ],
                        gap=4,
                    ),
                    dmc.Group(
                        [
                            dmc.Stack(
                                [dmc.Text("Source", size="xs", c="dimmed", tt="uppercase"), dmc.Text(str(status_meta.get("source")), size="sm", fw=600)],
                                gap=2,
                            ),
                            dmc.Stack(
                                [dmc.Text("As of", size="xs", c="dimmed", tt="uppercase"), dmc.Text(format_timestamp(status_meta.get("as_of")), size="sm", fw=600)],
                                gap=2,
                            ),
                            dmc.Stack(
                                [dmc.Text("Scope", size="xs", c="dimmed", tt="uppercase"), dmc.Text(str(status_meta.get("scope")), size="sm", fw=600)],
                                gap=2,
                            ),
                            html.Button("Refresh Data", id="refresh-button", n_clicks=0, className="refresh-button"),
                        ],
                        gap="md",
                    ),
                ],
                justify="space-between",
                align="flex-start",
                wrap="wrap",
            ),
            nav_row,
        ],
        gap="md",
    )
    top_alerts = [dmc.Alert(color="yellow", title="Notice", children=w, mb="sm") for w in (warnings or [])]
    eb = error_box(errors or [])
    body_list: list = top_alerts + ([eb] if eb else [])
    if isinstance(children, list):
        body_list.extend(children)
    else:
        body_list.append(children)
    return html.Div(
        className="app-shell",
        children=[
            dmc.Paper(children=[frame], p="lg", radius="xl", withBorder=True, className="app-frame"),
            html.Div(className="page-body-wrap", children=[html.Div(className="page-body", children=body_list)]),
        ],
    )


def fatal_error_page(title: str, errors: list[str], guidance: list[str] | None = None) -> html.Div:
    guidance = guidance or []
    return app_shell(
        [
            section_panel(
                title,
                [
                    html.Div("The dashboard could not finish loading its data.", className="terminal-caption"),
                    error_box(errors) or html.Div("Unknown error", className="empty-state"),
                    html.Div(className="guidance-list", children=[html.Div(item, className="guidance-item") for item in guidance]),
                ],
                subtitle="Load error",
                extra_class="fatal-panel",
            )
        ],
        page_title="Dashboard load error",
        active_page="overview",
        status_meta={"scope": "Load failure", "as_of": None, "source": "—"},
    )
