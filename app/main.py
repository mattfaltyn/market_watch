from __future__ import annotations

import dash
from dash import Input, Output, State, dcc, html

from app.components.ui import APP_CSS
from app.config import ROOT_DIR, load_config
from app.data.cache import FileCache
from app.data.yfinance_client import CachePolicy, MarketDataClient
from app.routing import dispatch_page_safe, refresh_state_payload

CONFIG = load_config()
CACHE = FileCache(ROOT_DIR / ".cache", default_ttl_seconds=int(CONFIG.cache.get("default_ttl_seconds", 3600)))
CLIENT = MarketDataClient(
    cache=CACHE,
    policy=CachePolicy(
        market_ttl_seconds=int(CONFIG.cache.get("market_ttl_seconds", 900)),
        fundamentals_ttl_seconds=int(CONFIG.cache.get("fundamentals_ttl_seconds", 21600)),
        news_ttl_seconds=int(CONFIG.cache.get("news_ttl_seconds", 1800)),
    ),
)


def create_app() -> dash.Dash:
    app = dash.Dash(__name__, suppress_callback_exceptions=True, title="KISS Portfolio")
    app.index_string = f"""
<!DOCTYPE html>
<html>
    <head>
        {{%metas%}}
        <title>{{%title%}}</title>
        {{%favicon%}}
        {{%css%}}
        <style>{APP_CSS}</style>
    </head>
    <body>
        {{%app_entry%}}
        <footer>
            {{%config%}}
            {{%scripts%}}
            {{%renderer%}}
        </footer>
    </body>
</html>
"""
    app.layout = html.Div(
        [
            dcc.Location(id="url"),
            dcc.Store(id="refresh-state", data={"refresh": 0}),
            html.Div(id="page-container"),
        ]
    )

    @app.callback(Output("refresh-state", "data"), Input("refresh-button", "n_clicks"), State("refresh-state", "data"))
    def refresh_data(n_clicks, current):  # pragma: no cover
        return refresh_state_payload(n_clicks, current)

    @app.callback(Output("page-container", "children"), Input("url", "pathname"), Input("refresh-state", "data"))
    def route(pathname: str, refresh_state: dict[str, int]):  # pragma: no cover
        return dispatch_page_safe(pathname, refresh_state, dash.ctx.triggered_id, client=CLIENT, config=CONFIG)

    return app


app = create_app()
server = app.server


if __name__ == "__main__":  # pragma: no cover
    app.run(debug=True)
