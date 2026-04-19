from __future__ import annotations

import dash
from dash import Input, Output, State, dcc, html

from app.components.ui import APP_CSS, fatal_error_page
from app.config import ROOT_DIR, load_config
from app.data.cache import FileCache
from app.data.defeatbeta_client import CachePolicy, DefeatBetaClient
from app.pages.overview import render_overview
from app.pages.ticker_detail import render_ticker_detail
from app.pages.watchlist import render_watchlist
from app.services.market_snapshot import build_market_snapshot, build_rates_snapshot
from app.services.signals import compute_regime, get_alert_flags
from app.services.watchlist_snapshot import build_watchlist_snapshot, get_ticker_detail


CONFIG = load_config()
CACHE = FileCache(ROOT_DIR / ".cache", default_ttl_seconds=int(CONFIG.cache.get("default_ttl_seconds", 3600)))
CLIENT = DefeatBetaClient(
    cache=CACHE,
    policy=CachePolicy(
        market_ttl_seconds=int(CONFIG.cache.get("market_ttl_seconds", 900)),
        fundamentals_ttl_seconds=int(CONFIG.cache.get("fundamentals_ttl_seconds", 21600)),
        news_ttl_seconds=int(CONFIG.cache.get("news_ttl_seconds", 1800)),
        filings_ttl_seconds=int(CONFIG.cache.get("filings_ttl_seconds", 21600)),
        transcripts_ttl_seconds=int(CONFIG.cache.get("transcripts_ttl_seconds", 43200)),
    ),
)


def _should_force_refresh(triggered_id: str | None, refresh_state: dict[str, int] | None) -> bool:
    return bool(triggered_id == "refresh-state" and refresh_state and refresh_state.get("refresh", 0) > 0)


def create_app() -> dash.Dash:
    app = dash.Dash(__name__, suppress_callback_exceptions=True, title="Market Watch")
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
    def refresh_data(n_clicks, current):
        return {"refresh": n_clicks or 0, "last": current.get("last") if current else 0}

    @app.callback(Output("page-container", "children"), Input("url", "pathname"), Input("refresh-state", "data"))
    def route(pathname: str, refresh_state: dict[str, int]):
        force_refresh = _should_force_refresh(dash.ctx.triggered_id, refresh_state)
        try:
            errors: list[str] = []

            if pathname and pathname.startswith("/ticker/"):
                symbol = pathname.split("/")[-1].upper()
                watchlist = build_watchlist_snapshot(CLIENT, [symbol], CONFIG.benchmark, CONFIG.alert_thresholds, force_refresh=force_refresh)
                rate_snapshot = build_rates_snapshot(CLIENT, force_refresh=force_refresh)
                flags = get_alert_flags(symbol, watchlist.iloc[0] if not watchlist.empty else {}, rate_snapshot, CONFIG.alert_thresholds)
                bundle = get_ticker_detail(CLIENT, symbol, flags, force_refresh=force_refresh)
                return render_ticker_detail(bundle)

            rates = build_rates_snapshot(CLIENT, force_refresh=force_refresh)
            watchlist = build_watchlist_snapshot(CLIENT, CONFIG.watchlist, CONFIG.benchmark, CONFIG.alert_thresholds, force_refresh=force_refresh)

            if pathname == "/watchlist":
                return render_watchlist(watchlist, errors)

            market = build_market_snapshot(CLIENT, force_refresh=force_refresh)
            regime = compute_regime(market, rates, watchlist)
            sp500_history_result = CLIENT.get_sp500_history(force_refresh=force_refresh)
            errors.extend(sp500_history_result.errors)
            return render_overview(market, rates, regime, watchlist, sp500_history_result.data, errors)
        except Exception as exc:  # pragma: no cover - callback boundary
            return fatal_error_page(
                title="Unable to load market data",
                errors=[str(exc)],
                guidance=[
                    "Confirm you have network access to the defeatbeta-api upstream data source.",
                    "Try the Refresh Data button after the initial data cache is populated.",
                    "Check the terminal for the full traceback if the problem persists.",
                ],
            )

    return app


app = create_app()
server = app.server


if __name__ == "__main__":
    app.run(debug=True)
