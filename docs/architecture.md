# Architecture

## Overview

`market_watch` is a **local-first** Plotly Dash application. A single location-based callback in [`app/main.py`](../app/main.py) loads data through a shared [`DefeatBetaClient`](../app/data/defeatbeta_client.py) and renders the appropriate page from [`app/pages/`](../app/pages/).

## Layers

| Layer | Role |
|-------|------|
| **UI** | Dash layout callbacks, [`app/components/ui.py`](../app/components/ui.py) |
| **Pages** | Route-specific composition in [`app/pages/`](../app/pages/) |
| **Services** | Regime, VAMS, portfolio, market snapshots in [`app/services/`](../app/services/) |
| **Data** | [`DefeatBetaClient`](../app/data/defeatbeta_client.py) wraps `defeatbeta-api` with optional [`yfinance`](../app/data/yfinance_client.py) fallback for missing series; [`FileCache`](../app/data/cache.py) persists pickled frames |
| **Config** | [`app/config.py`](../app/config.py) loads [`config/settings.yaml`](../config/settings.yaml) |

## Data flow

```mermaid
flowchart LR
  subgraph ui [Dash UI]
    main[app/main.py]
  end
  subgraph services [Services]
    regime_hist[regime_history]
    kiss_reg[kiss_regime]
    vams[vams]
    portfolio[kiss_portfolio]
    mkt[market_snapshot]
    wl[watchlist_snapshot]
  end
  subgraph data [Data layer]
    client[DefeatBetaClient]
    yf[yfinance_client]
    cache[FileCache]
  end
  main --> regime_hist
  main --> kiss_reg
  main --> vams
  main --> portfolio
  main --> mkt
  main --> wl
  regime_hist --> client
  kiss_reg --> client
  vams --> client
  portfolio --> client
  mkt --> client
  wl --> client
  client --> yf
  client --> cache
```

## Core services

- **`kiss_regime`** — Current macro quadrant from growth/inflation proxy scores (point-in-time).
- **`regime_history`** — Historical replay of the same proxy logic, indicator tape snapshots, confirmation bundles, and transition strips (`build_regime_overview_snapshot`).
- **`vams`** — Trend, momentum, volatility scoring; `get_vams_signal_history` for replay.
- **`kiss_portfolio`** — Legacy target/actual weights for `/implementation` only.
- **`market_snapshot` / signals`** — Market-wide and per-symbol alert context.
- **`watchlist_snapshot`** — Watchlist rows and ticker detail bundles for `/ticker/<symbol>`.

## Price symbols and data sources

[`DefeatBetaClient.get_prices`](../app/data/defeatbeta_client.py) loads the **logical** symbol from defeatbeta first. If the series is empty, it falls back to Yahoo Finance via [`fetch_prices_yfinance`](../app/data/yfinance_client.py) (same column shape). [`last_price_source`](../app/data/defeatbeta_client.py) records `defeatbeta` vs `yfinance` for optional UI labels. Optionally, `kiss.price_fetch_overrides` can still map a logical symbol to another defeatbeta ticker before the yfinance step. See [configuration.md](configuration.md) and [data-and-caching.md](data-and-caching.md).

## Regime inputs when data is missing

[`kiss_regime`](../app/services/kiss_regime.py) records unavailable proxy components in `KissRegime.unavailable_components` and omits them from composite means. [`build_regime_overview_snapshot`](../app/services/regime_history.py) surfaces warnings on the regime and signals pages.

## Models

Shared dataclasses live in [`app/models.py`](../app/models.py) (e.g. `KissRegime`, `RegimeOverviewSnapshot`, `VamsSignal`, `TickerDetailBundle`).
