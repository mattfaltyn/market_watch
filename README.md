# market_watch

Local-first KISS regime and market-indicators terminal built with Plotly Dash and **Yahoo Finance** (`yfinance`).

## Documentation

| Doc | Description |
|-----|-------------|
| [AGENTS.md](AGENTS.md) | Contributor and coding-agent guide (setup, verification, repo map) |
| [docs/README.md](docs/README.md) | Index of technical documentation |
| [docs/architecture.md](docs/architecture.md) | Layers, data flow, core services |
| [docs/configuration.md](docs/configuration.md) | `settings.yaml` and `AppConfig` |
| [docs/data-and-caching.md](docs/data-and-caching.md) | yfinance client, file cache, refresh |
| [docs/development.md](docs/development.md) | Venv, tests, conventions |
| [docs/testing.md](docs/testing.md) | Parallel pytest, branch coverage, coverage reports |
| [docs/routing-and-pages.md](docs/routing-and-pages.md) | URL routes and page modules |

## What This App Does

This app is no longer a portfolio-implementation dashboard. It is a regime-and-indicators KISS app that answers:

- what macro regime are we in right now
- how strong is that regime
- what changed recently
- which indicators are driving the call
- whether key assets are confirming the macro backdrop

The current UI is intentionally visual-first and dark by default:

- the home page is a regime state board
- the shell uses a compact static dark terminal layout with live status and page navigation
- regime is shown as a growth / inflation quadrant
- confirmation assets are shown through cards, gauges, chips, and transition rails
- market indicators are shown as a tape and heat strips
- watchlist and audit surfaces use dark custom tables instead of a bright spreadsheet-like treatment
- shared spacing is driven by semantic layout regions instead of route-specific one-off gaps
- text is secondary to charts, bars, and signal encoding

The core confirmation assets are:

- equities: `SPY`
- fixed income: `AGG`
- bitcoin: `BTC-USD`

## KISS Methodology

KISS still uses the same regime logic:

The app classifies the current macro state into one of four regimes using growth and inflation proxy scores:

- `goldilocks`: growth up, inflation down
- `reflation`: growth up, inflation up
- `inflation`: growth down, inflation up
- `deflation`: growth down, inflation down

The app also keeps VAMS, but now as confirmation rather than portfolio sizing:

- `bullish` = `100%` of target
- `neutral` = `50%` of target
- `bearish` = `0%` of target

In the current product, those states are interpreted as:

- `SPY` = equity confirmation
- `AGG` = bond confirmation
- `BTC-USD` = risk appetite confirmation

**Data sources:** Prices, treasury proxies, S&P 500 annual history, and ticker fundamentals/news load through **`yfinance`** (Yahoo Finance). Tiles may show **via Yahoo Finance**. The **10Y − 5Y (proxy)** spread uses the **`bc2_year`** column, which is populated from the **5Y** index proxy `^FVX` (not a true 2Y; see [docs/data-and-caching.md](docs/data-and-caching.md)). Regime proxy inputs with no data are called out in warnings and omitted from composite means (see [docs/architecture.md](docs/architecture.md)).

## Signal Design

### Macro Regime Engine

The macro engine is implemented in [app/services/kiss_regime.py](app/services/kiss_regime.py). It uses configured proxy inputs and classifies the quadrant from normalized growth and inflation scores.

Default growth proxies:

- `SPY` medium-term trend
- cyclical vs defensive ratio: `XLY / XLP`
- copper vs gold ratio: `CPER / GLD`

Default inflation proxies:

- `10Y` Treasury yield trend
- oil trend: `USO`
- commodity basket trend: `DBC`

### VAMS Engine

The sleeve-level engine is implemented in [app/services/vams.py](app/services/vams.py). It uses:

- trend: price vs configured moving averages
- momentum: blended `1M` and `3M` returns
- volatility: realized volatility penalty

The result is a sleeve state of `bullish`, `neutral`, or `bearish`.

### Historical Regime And Confirmation Replay

Historical regime replay lives in [app/services/regime_history.py](app/services/regime_history.py). It replays the current growth/inflation logic across Yahoo Finance time series to derive:

- regime history
- last regime flip
- recent indicator changes
- last VAMS confirmation transition for `SPY`, `AGG`, and `BTC-USD`

The app does not rely on in-session app memory for these transitions.

## Routes

- `/`: **Overview** — regime hero, quadrant, transitions, confirmation assets, indicator tape, and diagnostics (merged former Signals content).
- `/markets`: macro telemetry (benchmark tape, rates, curve, breadth, participation, S&P context). Old URL `/market-watch` redirects here.
- `/watchlist`: watchlist snapshot table with links to tickers.
- `/ticker/<symbol>`: regime intelligence drill-down for configured sleeves and supported symbols.

## Run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
python -m app.main
```

Open `http://127.0.0.1:8050`.

## Configuration

Methodology is configured in [config/settings.yaml](config/settings.yaml).

Key sections:

- `kiss.sleeves`: symbol mapping for confirmation assets
- `kiss.base_weights` / `kiss.regime_rules` / `kiss.vams_multipliers`: methodology and VAMS parameters used by confirmation logic
- `kiss.regime_inputs`: proxy symbols and weak-score threshold for macro classification
- `kiss.market_watch_symbols`: symbols shown on the Markets page and related snapshots
- `alert_thresholds`: VAMS state thresholds, large move thresholds, and volatility limits
- `chart_windows`: moving-average and lookback windows
- `cache`: TTL configuration by data category

The config loader is defined in [app/config.py](app/config.py).

## Data And Runtime Notes

- The app fetches live data through **Yahoo Finance** (`yfinance`); initial page loads require network access and are subject to Yahoo availability and rate limits.
- If the upstream source is unavailable, the app renders an in-app error state instead of a blank page.
- `BTC-USD` is the default bitcoin sleeve proxy in v1.
- Regime transitions and confirmation transitions are derived from historical series at request time (cached under `.cache/`).
- The `/ticker/<symbol>` drill-down does **not** include SEC filings, transcripts, or revenue segment/geography tables (not exposed by `yfinance` in this app).
- The primary product does not depend on app-session memory for “what changed”.
- There is no persisted history, rebalance ledger, or trade execution integration in v1.
- The macro regime and VAMS methodologies are approximate and explainable local proxies, not a claim of exact proprietary 42 Macro replication.
- The UI keeps tabular audit surfaces available through custom dark tables, but the product is designed to be understood visually before reading detailed text.

## Development

Run the test suite from the repo-local venv:

```bash
.venv/bin/pytest -q
```

Optional app bootstrap check:

```bash
.venv/bin/python -c "from app.main import create_app; app=create_app(); print(type(app).__name__)"
```

## Structure

- [app/main.py](app/main.py): Dash entrypoint and routing
- [app/data/](app/data): file cache and `MarketDataClient` (`yfinance`)
- [app/services/](app/services): KISS regime, regime history replay, VAMS confirmation, and supporting market logic
- [app/pages/](app/pages): overview, markets, watchlist, and ticker detail views
- [config/](config): YAML methodology, sleeve mappings, and thresholds
- [tests/](tests): cache, KISS services, regime history, watchlist, and page rendering tests
- [docs/](docs): technical documentation (architecture, configuration, caching, development, routing)
- [AGENTS.md](AGENTS.md): contributor and agent guide
