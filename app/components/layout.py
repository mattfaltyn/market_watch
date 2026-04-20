"""App shell and top-level layout."""

from __future__ import annotations

import dash_mantine_components as dmc
from dash import dcc, html

from app.components.primitives import error_box, format_timestamp, normalize_status_meta, section_panel


def _nav_link(label: str, href: str, active: bool) -> dcc.Link:
    return dcc.Link(
        html.Div(label, className=f"nav-pill {'is-active' if active else ''}".strip()),
        href=href,
        className="nav-link",
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
    nav_row = html.Div([_nav_link(label, href, active_page == key) for label, href, key in nav], className="shell-nav")
    status_cards = [
        html.Div(
            [
                html.Div(label, className="status-label"),
                html.Div(value, className="status-value"),
            ],
            className="status-pill",
        )
        for label, value in [
            ("Source", str(status_meta.get("source"))),
            ("As Of", format_timestamp(status_meta.get("as_of"))),
            ("Scope", str(status_meta.get("scope"))),
        ]
    ]
    frame = dmc.Stack(
        [
            html.Div(
                className="shell-top",
                children=[
                    html.Div(
                        className="shell-brand",
                        children=[
                            html.Div("KISS / MARKET REGIME", className="shell-kicker"),
                            html.Div(
                                className="shell-title-row",
                                children=[
                                    dmc.Title("KISS Terminal", order=1, className="shell-title"),
                                ],
                            ),
                            html.Div(page_title, className="shell-subtitle"),
                        ],
                    ),
                    html.Div(
                        className="shell-status",
                        children=[
                            html.Div(status_cards, className="status-grid"),
                            html.Button("Refresh Data", id="refresh-button", n_clicks=0, className="refresh-button"),
                        ],
                    ),
                ],
            ),
            nav_row,
        ],
        gap="xs",
        className="shell-stack",
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
            dmc.Paper(children=[frame], p="md", radius="xl", withBorder=True, className="app-frame"),
            html.Div(className="page-body-wrap", children=[html.Div(className="page-body page-stack", children=body_list)]),
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
