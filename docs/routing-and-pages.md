# Routing and pages

Routing is implemented in the `route` callback in [`app/main.py`](../app/main.py) (`Input("url", "pathname")` and refresh store).

| Path | Renderer | Notes |
|------|----------|--------|
| `/` (default) | [`render_regime_overview`](../app/pages/overview.py) | Uses `build_regime_overview_snapshot` — quadrant, transitions, tape, confirmations. |
| `/signals` | [`render_signals`](../app/pages/signals.py) | Same snapshot; charts and tables for regime history and confirmation. |
| `/market-watch` | [`render_market_watch`](../app/pages/market_watch.py) | Market snapshot, rates, SP500 history, indicator list from config. |
| `/implementation` | [`render_implementation`](../app/pages/implementation.py) | Legacy KISS portfolio snapshot (`get_kiss_regime` + `get_vams_signals` + `build_kiss_portfolio_snapshot`). |
| `/ticker/<symbol>` | [`render_ticker_detail`](../app/pages/ticker_detail.py) | Symbol must be in `market_watch_symbols` or `sleeve_symbols`. |

Unknown paths fall through to the **regime overview** (same as `/`) in the current callback structure.

## Navigation shell

Shared chrome and nav labels are built in [`app/components/ui.py`](../app/components/ui.py) (`app_shell`, active page ids: `regime`, `signals`, `market-watch`, etc.). Implementation is reachable by URL but may not appear in the primary nav.

## Errors

- Unsupported ticker: `fatal_error_page` with guidance.
- Load exceptions: `fatal_error_page` with traceback message and network/cache hints.
