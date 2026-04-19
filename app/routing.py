from __future__ import annotations

from typing import Any

import pandas as pd

from app.components.ui import fatal_error_page
from app.config import AppConfig
from app.pages.implementation import render_implementation
from app.pages.market_watch import render_market_watch
from app.pages.overview import render_regime_overview
from app.pages.signals import render_signals
from app.pages.ticker_detail import render_ticker_detail
from app.services.kiss_portfolio import build_kiss_portfolio_snapshot
from app.services.kiss_regime import get_kiss_regime
from app.services.market_snapshot import build_market_snapshot, build_rates_snapshot
from app.services.regime_history import build_regime_overview_snapshot
from app.services.signals import get_alert_flags
from app.services.vams import get_vams_signals
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
        return render_ticker_detail(bundle)

    if pathname == "/implementation":
        regime = get_kiss_regime(client, config, force_refresh=force_refresh)
        vams_signals = get_vams_signals(
            client,
            [config.sleeves["equity"], config.sleeves["fixed_income"], config.sleeves["bitcoin"]],
            config.alert_thresholds,
            force_refresh=force_refresh,
        )
        kiss_snapshot = build_kiss_portfolio_snapshot(regime, vams_signals, config)
        return render_implementation(kiss_snapshot, errors)
    regime_snapshot = build_regime_overview_snapshot(client, config, force_refresh=force_refresh)
    errors.extend(regime_snapshot.warnings)
    if pathname == "/signals":
        return render_signals(regime_snapshot, errors)

    if pathname == "/market-watch":
        rates = build_rates_snapshot(client, force_refresh=force_refresh)
        market = build_market_snapshot(client, symbols=config.market_watch_symbols, force_refresh=force_refresh)
        sp500_history_result = client.get_sp500_history(force_refresh=force_refresh)
        errors.extend(sp500_history_result.errors)
        indicator_frame = pd.DataFrame({"symbol": config.market_watch_symbols})
        return render_market_watch(market, rates, indicator_frame, sp500_history_result.data, errors)

    return render_regime_overview(regime_snapshot, errors)


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
