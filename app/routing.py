from __future__ import annotations

from typing import Any

from app.components.ui import fatal_error_page
from app.config import AppConfig
from app.pages.markets import render_markets
from app.pages.overview import render_regime_overview
from app.pages.ticker_detail import render_ticker_detail
from app.pages.watchlist import render_watchlist
from app.services.market_snapshot import build_market_snapshot, build_rates_snapshot
from app.services.regime_history import build_regime_overview_snapshot
from app.services.signals import get_alert_flags
from app.services.watchlist_snapshot import build_watchlist_snapshot, get_ticker_detail


def _should_force_refresh(triggered_id: str | None, refresh_state: dict[str, int] | None) -> bool:
    return bool(triggered_id == "refresh-state" and refresh_state and refresh_state.get("refresh", 0) > 0)


def refresh_state_payload(n_clicks: int | None, current: dict[str, int] | None) -> dict[str, int]:
    """Dash refresh callback: store latest click count and preserve last metadata."""
    return {"refresh": n_clicks or 0, "last": current.get("last") if current else 0}


def dispatch_page(
    pathname: str | None,
    refresh_state: dict[str, int] | None,
    triggered_id: str | None,
    *,
    client: Any,
    config: AppConfig,
):
    """Build Dash page children for a URL path. Used by the Dash callback and unit tests."""
    force_refresh = _should_force_refresh(triggered_id, refresh_state)
    pathname = pathname or "/"
    if pathname == "/market-watch":
        pathname = "/markets"
    errors: list[str] = []

    if pathname and pathname.startswith("/ticker/"):
        symbol = pathname.split("/")[-1].upper()
        allowed_symbols = set(config.market_watch_symbols + config.sleeve_symbols)
        if symbol not in allowed_symbols:
            return fatal_error_page(
                title="Unsupported ticker route",
                errors=[f"{symbol} is not configured for KISS detail views."],
                guidance=["Use configured sleeve assets or configured market-watch indicators."],
            )
        watchlist = build_watchlist_snapshot(client, [symbol], config.sleeves["equity"], config.alert_thresholds, force_refresh=force_refresh)
        rate_snapshot = build_rates_snapshot(client, force_refresh=force_refresh)
        flags = get_alert_flags(symbol, watchlist.iloc[0] if not watchlist.empty else {}, rate_snapshot, config.alert_thresholds)
        role_map = {
            config.sleeves["equity"]: "Equity confirmation",
            config.sleeves["fixed_income"]: "Bond confirmation",
            config.sleeves["bitcoin"]: "Risk appetite confirmation",
        }
        bundle = get_ticker_detail(client, symbol, flags, force_refresh=force_refresh, role_label=role_map.get(symbol))
        return render_ticker_detail(bundle, config)

    regime_snapshot = build_regime_overview_snapshot(client, config, force_refresh=force_refresh)
    errors.extend(regime_snapshot.warnings)

    if pathname == "/watchlist":
        frame = build_watchlist_snapshot(
            client, config.market_watch_symbols, config.sleeves["equity"], config.alert_thresholds, force_refresh=force_refresh
        )
        return render_watchlist(frame, errors, config)

    if pathname == "/markets":
        rates = build_rates_snapshot(client, force_refresh=force_refresh)
        market = build_market_snapshot(client, symbols=config.market_watch_symbols, force_refresh=force_refresh)
        sp500_history_result = client.get_sp500_history(force_refresh=force_refresh)
        errors.extend(sp500_history_result.errors)
        return render_markets(market, rates, sp500_history_result.data, errors, config)

    return render_regime_overview(regime_snapshot, errors, config)


def dispatch_page_safe(
    pathname: str | None,
    refresh_state: dict[str, int] | None,
    triggered_id: str | None,
    *,
    client: Any,
    config: AppConfig,
):
    """Like ``dispatch_page`` but maps unexpected exceptions to a fatal error page (Dash callback boundary)."""
    try:
        return dispatch_page(pathname, refresh_state, triggered_id, client=client, config=config)
    except Exception as exc:
        return fatal_error_page(
            title="Unable to load market data",
            errors=[str(exc)],
            guidance=[
                "Confirm you have network access to Yahoo Finance (yfinance).",
                "Try the Refresh Data button after the initial data cache is populated.",
                "Check the terminal for the full traceback if the problem persists.",
            ],
        )
