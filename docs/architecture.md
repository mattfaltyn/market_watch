# Architecture

## Overview

The app is a single-page Dash application: `create_app()` in [`app/main.py`](../app/main.py) sets `app.layout` from [`create_app_layout()`](../app/dashboard.py) (root stores, header, chart-range control, and `page-container`). One callback refreshes the `refresh-state` store; another updates the error banner, “last updated” text, `history-store`, and main content by calling [`run_dashboard_fetch()`](../app/dashboard.py).

## Data flow

1. **Config** — [`load_config()`](../app/config.py) reads [`config/settings.yaml`](../config/settings.yaml) into `AppConfig` (symbol, default range, moving averages, cache TTLs).
2. **Cache** — [`FileCache`](../app/data/cache.py) persists pickled payloads under `.cache/`.
3. **Client** — [`BitcoinDataClient`](../app/data/bitcoin_client.py) uses `yfinance` to load daily OHLCV for `BTC-USD`, normalizes columns (`report_date`, OHLCV), and uses `get_or_set` with `market_ttl_seconds` unless `force_refresh` is requested after **Refresh**.
4. **Metrics** — [`app/metrics.py`](../app/metrics.py) derives returns, ATH distance, realized vol, MA states, drawdown, and chart slices from the full history frame.
5. **UI** — [`build_page_content()`](../app/dashboard.py) composes hero, chart (`dcc.Graph`), stat rail, and supporting cards; styles come from [`assets/theme.css`](../assets/theme.css) and [`app/components/theme.py`](../app/components/theme.py) (Mantine + Plotly template).

## Error handling

The client returns [`DataResult`](../app/models.py) with an empty frame and `errors` instead of raising for expected failures. The dashboard merges new errors with prior cached history when a refresh fails so the layout can stay visible with a top alert.
