from __future__ import annotations

import dash
import dash_mantine_components as dmc
from dash import Input, Output, State

from app.config import ROOT_DIR, load_config
from app.dashboard import create_app_layout, refresh_state_payload, run_dashboard_fetch
from app.data.bitcoin_client import BitcoinDataClient
from app.data.cache import FileCache

CONFIG = load_config()
CACHE = FileCache(ROOT_DIR / ".cache", default_ttl_seconds=int(CONFIG.cache.default_ttl_seconds))
CLIENT = BitcoinDataClient(
    cache=CACHE,
    symbol=CONFIG.dashboard.symbol,
    market_ttl_seconds=int(CONFIG.cache.market_ttl_seconds),
    moving_averages=tuple(CONFIG.dashboard.moving_averages),
)


def create_app() -> dash.Dash:
    app = dash.Dash(__name__, suppress_callback_exceptions=True, title="Bitcoin Market Watch")
    app.layout = create_app_layout(CONFIG)

    @app.callback(Output("refresh-state", "data"), Input("refresh-button", "n_clicks"), State("refresh-state", "data"))
    def refresh_data(n_clicks, current):  # pragma: no cover
        return refresh_state_payload(n_clicks, current)

    @app.callback(
        Output("error-banner-container", "children"),
        Output("header-updated", "children"),
        Output("history-store", "data"),
        Output("page-container", "children"),
        Input("url", "pathname"),
        Input("range-select", "value"),
        Input("refresh-state", "data"),
        State("history-store", "data"),
    )
    def render_dashboard(pathname, range_value, refresh_state, hist_store):  # pragma: no cover
        triggered_id = dash.ctx.triggered_id
        banner, header_ts, store, body = run_dashboard_fetch(
            triggered_id,
            range_value,
            refresh_state,
            hist_store,
            CLIENT,
            CONFIG,
        )
        return banner, header_ts, store, body

    return app


app = create_app()
server = app.server


if __name__ == "__main__":  # pragma: no cover
    app.run(debug=True)
