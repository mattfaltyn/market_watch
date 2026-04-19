# market_watch

Local-first KISS regime and market-indicators terminal built with Plotly Dash and `defeatbeta-api`.

## Documentation

| Doc | Description |
|-----|-------------|
| [AGENTS.md](AGENTS.md) | Contributor and coding-agent guide (setup, verification, repo map) |
| [docs/README.md](docs/README.md) | Index of technical documentation |
| [docs/architecture.md](docs/architecture.md) | Layers, data flow, core services |
| [docs/configuration.md](docs/configuration.md) | `settings.yaml` and `AppConfig` |
| [docs/data-and-caching.md](docs/data-and-caching.md) | defeatbeta client, file cache, refresh |
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

The current UI is intentionally visual-first:

- the home page is a regime state board
- regime is shown as a growth / inflation quadrant
- confirmation assets are shown through cards, gauges, chips, and transition rails
- market indicators are shown as a tape and heat strips
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

**Data sources:** Prices load from **defeatbeta-api** first; if a logical symbol has no series there, **Yahoo Finance** (`yfinance`) supplies history for the same ticker. Tiles may show **via Yahoo Finance** when applicable. Regime proxy inputs with no data are called out in warnings and omitted from composite means (see [docs/architecture.md](docs/architecture.md)).

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

Historical regime replay lives in [app/services/regime_history.py](app/services/regime_history.py). It replays the current growth/inflation logic across defeatbeta-api time series to derive:

- regime history
- last regime flip
- recent indicator changes
- last VAMS confirmation transition for `SPY`, `AGG`, and `BTC-USD`

The app does not rely on in-session app memory for these transitions.

## Routes

- `/`: regime overview homepage with quadrant, transitions, indicator tape, and confirmation assets.
- `/signals`: detailed regime diagnostics, historical replay, decomposition, and VAMS confirmation state.
- `/market-watch`: broader macro telemetry wall for indicators, yields, commodities, and participation.
- `/ticker/<symbol>`: regime intelligence drill-down for configured sleeves and supported symbols.
- `/implementation`: legacy allocation route retained temporarily, but no longer part of the primary product framing.

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

- `kiss.sleeves`: symbol mapping for confirmation assets and the legacy allocation route
- `kiss.base_weights`: retained for the legacy implementation route
- `kiss.regime_rules`: retained for the legacy implementation route
- `kiss.vams_multipliers`: VAMS thresholds and multipliers used by confirmation logic and the legacy implementation route
- `kiss.regime_inputs`: proxy symbols and weak-score threshold for macro classification
- `kiss.market_watch_symbols`: symbols shown on the supporting market-watch page
- `kiss.price_fetch_overrides`: optional map from a logical symbol (for example `AGG`, `BTC-USD`) to a defeatbeta ticker that has price history when the primary symbol does not
- `alert_thresholds`: VAMS state thresholds, large move thresholds, and volatility limits
- `chart_windows`: moving-average and lookback windows
- `cache`: TTL configuration by data category

The config loader is defined in [app/config.py](app/config.py).

## Data And Runtime Notes

- The app fetches live data through `defeatbeta-api`, so initial page loads require network access to the upstream dataset.
- If the upstream source is unavailable, the app renders an in-app error state instead of a blank page.
- `BTC-USD` is the default bitcoin sleeve proxy in v1.
- Regime transitions and confirmation transitions are derived from defeatbeta-api historical series at request time.
- The primary product does not depend on app-session memory for “what changed”.
- There is no persisted history, rebalance ledger, or trade execution integration in v1.
- The macro regime and VAMS methodologies are approximate and explainable local proxies, not a claim of exact proprietary 42 Macro replication.
- The UI intentionally keeps `dash_table.DataTable` as a secondary audit surface, but the product is designed to be understood visually before reading detailed text.

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
- [app/data/](app/data): cache and `defeatbeta-api` adapter
- [app/services/](app/services): KISS regime, regime history replay, VAMS confirmation, legacy portfolio construction, and supporting market logic
- [app/pages/](app/pages): regime overview, legacy implementation, signals, market-watch, and ticker detail views
- [config/](config): YAML methodology, sleeve mappings, and thresholds
- [tests/](tests): cache, KISS services, signals, watchlist support, and page rendering tests
- [docs/](docs): technical documentation (architecture, configuration, caching, development, routing)
- [AGENTS.md](AGENTS.md): contributor and agent guide
