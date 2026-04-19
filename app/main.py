from __future__ import annotations

import dash
from dash import Input, Output, State, dcc, html

from app.components.ui import APP_CSS, fatal_error_page
from app.config import ROOT_DIR, load_config
from app.data.cache import FileCache
from app.data.defeatbeta_client import CachePolicy, DefeatBetaClient
from app.pages.implementation import render_implementation
from app.pages.market_watch import render_market_watch
from app.pages.overview import render_regime_overview
from app.pages.signals import render_signals
from app.pages.ticker_detail import render_ticker_detail
from app.services.market_snapshot import build_market_snapshot, build_rates_snapshot
from app.services.kiss_portfolio import build_kiss_portfolio_snapshot
from app.services.kiss_regime import get_kiss_regime
from app.services.regime_history import build_regime_overview_snapshot
from app.services.signals import get_alert_flags
from app.services.vams import get_vams_signals
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
    price_fetch_overrides=CONFIG.price_fetch_overrides,
)


def _should_force_refresh(triggered_id: str | None, refresh_state: dict[str, int] | None) -> bool:
    return bool(triggered_id == "refresh-state" and refresh_state and refresh_state.get("refresh", 0) > 0)


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
    def refresh_data(n_clicks, current):
        return {"refresh": n_clicks or 0, "last": current.get("last") if current else 0}

    @app.callback(Output("page-container", "children"), Input("url", "pathname"), Input("refresh-state", "data"))
    def route(pathname: str, refresh_state: dict[str, int]):
        force_refresh = _should_force_refresh(dash.ctx.triggered_id, refresh_state)
        try:
            errors: list[str] = []
            if pathname and pathname.startswith("/ticker/"):
                symbol = pathname.split("/")[-1].upper()
                allowed_symbols = set(CONFIG.market_watch_symbols + CONFIG.sleeve_symbols)
                if symbol not in allowed_symbols:
                    return fatal_error_page(
                        title="Unsupported ticker route",
                        errors=[f"{symbol} is not configured for KISS detail views."],
                        guidance=["Use configured sleeve assets or configured market-watch indicators."],
                    )
                watchlist = build_watchlist_snapshot(CLIENT, [symbol], CONFIG.sleeves["equity"], CONFIG.alert_thresholds, force_refresh=force_refresh)
                rate_snapshot = build_rates_snapshot(CLIENT, force_refresh=force_refresh)
                flags = get_alert_flags(symbol, watchlist.iloc[0] if not watchlist.empty else {}, rate_snapshot, CONFIG.alert_thresholds)
                role_map = {
                    CONFIG.sleeves["equity"]: "Equity confirmation",
                    CONFIG.sleeves["fixed_income"]: "Bond confirmation",
                    CONFIG.sleeves["bitcoin"]: "Risk appetite confirmation",
                }
                bundle = get_ticker_detail(CLIENT, symbol, flags, force_refresh=force_refresh, role_label=role_map.get(symbol))
                return render_ticker_detail(bundle)

            if pathname == "/implementation":
                regime = get_kiss_regime(CLIENT, CONFIG, force_refresh=force_refresh)
                vams_signals = get_vams_signals(
                    CLIENT,
                    [CONFIG.sleeves["equity"], CONFIG.sleeves["fixed_income"], CONFIG.sleeves["bitcoin"]],
                    CONFIG.alert_thresholds,
                    force_refresh=force_refresh,
                )
                kiss_snapshot = build_kiss_portfolio_snapshot(regime, vams_signals, CONFIG)
                return render_implementation(kiss_snapshot, errors)
            regime_snapshot = build_regime_overview_snapshot(CLIENT, CONFIG, force_refresh=force_refresh)
            if pathname == "/signals":
                return render_signals(regime_snapshot, errors)

            if pathname == "/market-watch":
                rates = build_rates_snapshot(CLIENT, force_refresh=force_refresh)
                market = build_market_snapshot(CLIENT, symbols=CONFIG.market_watch_symbols, force_refresh=force_refresh)
                sp500_history_result = CLIENT.get_sp500_history(force_refresh=force_refresh)
                errors.extend(sp500_history_result.errors)
                indicator_frame = __import__("pandas").DataFrame({"symbol": CONFIG.market_watch_symbols})
                return render_market_watch(market, rates, indicator_frame, sp500_history_result.data, errors)

            return render_regime_overview(regime_snapshot, errors)
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
