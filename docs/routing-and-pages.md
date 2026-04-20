# Routing and pages

Routing is implemented in the `route` callback in [`app/main.py`](../app/main.py) (`Input("url", "pathname")` and refresh store).

| Path | Renderer | Notes |
|------|----------|--------|
| `/` (default) | [`render_regime_overview`](../app/pages/overview.py) | Regime-first overview with hero summary, KPI rail, quadrant, transitions, indicator tape, and confirmation cards. Uses `build_regime_overview_snapshot`. |
| `/markets` | [`render_markets`](../app/pages/markets.py) | Benchmark tape, rates (levels vs deltas), yield curve, breadth, participation, S&P context chart. |
| `/watchlist` | [`render_watchlist`](../app/pages/watchlist.py) | Watchlist table with links to ticker drill-downs. |
| `/ticker/<symbol>` | [`render_ticker_detail`](../app/pages/ticker_detail.py) | Price/MAs, valuation, quality/growth, alerts, news. Symbol must be in `market_watch_symbols` or sleeve symbols. |

**Redirect:** `/market-watch` redirects to `/markets` (backward compatibility).

Unknown paths fall through to the **regime overview** (same as `/`) in the current callback structure.

## Navigation shell

Shared chrome and nav are built with **dash-mantine-components** and helpers in [`app/components/layout.py`](../app/components/layout.py) / [`app/components/ui.py`](../app/components/ui.py) (`app_shell`, active page ids: `overview`, `markets`, `watchlist`, `ticker`).

The shell is a compact static header rather than a sticky overlay. Page spacing is coordinated through shared semantic layout regions in the UI layer (`page-stack`, section rows, KPI rail, dense card grids, chart bands) so routes do not each invent their own top-of-page and section gap rules.

## Errors

- Unsupported ticker: `fatal_error_page` with guidance.
- Load exceptions: `fatal_error_page` with traceback message and network/cache hints.
