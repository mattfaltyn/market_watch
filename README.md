# market_watch

Local-first KISS portfolio dashboard built with Plotly Dash and `defeatbeta-api`.

## What This App Does

This app is no longer a generic market watch dashboard. It is an implementation-first KISS portfolio app that answers:

- what macro regime are we in right now
- what should the portfolio target be
- what is the actually implemented portfolio after VAMS scaling
- what changed since the prior update in the current app session
- what should be implemented now

The default sleeves are:

- equities: `SPY`
- fixed income: `AGG`
- bitcoin: `BTC-USD`
- cash or liquidity residual: `USFR`

## KISS Methodology

KISS starts with a base portfolio:

- equities: `60%`
- fixed income: `30%`
- bitcoin: `10%`

It then applies two overlays.

### 1. Top-Down Regime Overlay

The app classifies the current macro state into one of four regimes using growth and inflation proxy scores:

- `goldilocks`: growth up, inflation down
- `reflation`: growth up, inflation up
- `inflation`: growth down, inflation up
- `deflation`: growth down, inflation down

Those regimes map to target sleeve weights:

| Regime | SPY | AGG | BTC-USD |
| --- | ---: | ---: | ---: |
| Goldilocks | 60% | 30% | 10% |
| Reflation | 60% | 15% | 10% |
| Inflation | 30% | 15% | 5% |
| Deflation | 30% | 30% | 5% |

### 2. Bottom-Up VAMS Overlay

Each sleeve then gets a VAMS state:

- `bullish` = `100%` of target
- `neutral` = `50%` of target
- `bearish` = `0%` of target

Core formula:

`actual weight = regime target weight × VAMS multiplier`

Examples:

- BTC target `10%` with neutral VAMS -> actual `5%`
- SPY target `60%` with bearish VAMS -> actual `0%`
- AGG target `30%` with bullish VAMS -> actual `30%`

Residual weight is assigned to the cash sleeve, `USFR`.

## Signal Design

### Macro Regime Engine

The macro engine is implemented in [app/services/kiss_regime.py](/Users/mattfaltyn/Desktop/hypertrial_trilemma/trading/market_watch/app/services/kiss_regime.py). It uses configured proxy inputs and classifies the quadrant from normalized growth and inflation scores.

Default growth proxies:

- `SPY` medium-term trend
- cyclical vs defensive ratio: `XLY / XLP`
- copper vs gold ratio: `CPER / GLD`

Default inflation proxies:

- `10Y` Treasury yield trend
- oil trend: `USO`
- commodity basket trend: `DBC`

### VAMS Engine

The sleeve-level engine is implemented in [app/services/vams.py](/Users/mattfaltyn/Desktop/hypertrial_trilemma/trading/market_watch/app/services/vams.py). It uses:

- trend: price vs configured moving averages
- momentum: blended `1M` and `3M` returns
- volatility: realized volatility penalty

The result is a sleeve state of `bullish`, `neutral`, or `bearish`.

### Portfolio Construction

Portfolio construction lives in [app/services/kiss_portfolio.py](/Users/mattfaltyn/Desktop/hypertrial_trilemma/trading/market_watch/app/services/kiss_portfolio.py). It:

1. starts from the configured base mix
2. applies the regime rule table to get target weights
3. applies VAMS multipliers to get actual weights
4. sends the residual to `USFR`
5. computes deltas against the immediately previous in-memory snapshot

## Routes

- `/`: KISS Overview. Current regime, target allocation, actual allocation, implementation status, sleeve table, and action summary.
- `/implementation`: target vs actual portfolio construction with allocation visuals and sleeve-level gaps.
- `/signals`: regime diagnostics and sleeve-level VAMS diagnostics.
- `/market-watch`: supporting macro and market context page. This is secondary to the KISS implementation view.
- `/ticker/<symbol>`: detail page for configured sleeves and supported symbols.

## Run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
python -m app.main
```

Open `http://127.0.0.1:8050`.

## Configuration

Methodology is configured in [config/settings.yaml](/Users/mattfaltyn/Desktop/hypertrial_trilemma/trading/market_watch/config/settings.yaml).

Key sections:

- `kiss.sleeves`: symbol mapping for equity, fixed income, bitcoin, and cash sleeves
- `kiss.base_weights`: the baseline `60 / 30 / 10` portfolio
- `kiss.regime_rules`: target allocations for each regime
- `kiss.vams_multipliers`: multipliers for bullish, neutral, and bearish states
- `kiss.regime_inputs`: proxy symbols and weak-score threshold for macro classification
- `kiss.market_watch_symbols`: symbols shown on the supporting market-watch page
- `alert_thresholds`: VAMS state thresholds, large move thresholds, and volatility limits
- `chart_windows`: moving-average and lookback windows
- `cache`: TTL configuration by data category

The config loader is defined in [app/config.py](/Users/mattfaltyn/Desktop/hypertrial_trilemma/trading/market_watch/app/config.py).

## Data And Runtime Notes

- The app fetches live data through `defeatbeta-api`, so initial page loads require network access to the upstream dataset.
- If the upstream source is unavailable, the app renders an in-app error state instead of a blank page.
- `BTC-USD` is the default bitcoin sleeve proxy in v1.
- Portfolio deltas are only computed against the previous snapshot held in memory during the current app session.
- There is no persisted history, rebalance ledger, or trade execution integration in v1.
- The macro regime and VAMS methodologies are approximate and explainable local proxies, not a claim of exact proprietary 42 Macro replication.

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

- [app/main.py](/Users/mattfaltyn/Desktop/hypertrial_trilemma/trading/market_watch/app/main.py): Dash entrypoint and routing
- [app/data/](/Users/mattfaltyn/Desktop/hypertrial_trilemma/trading/market_watch/app/data): cache and `defeatbeta-api` adapter
- [app/services/](/Users/mattfaltyn/Desktop/hypertrial_trilemma/trading/market_watch/app/services): KISS regime, VAMS, portfolio construction, and supporting market logic
- [app/pages/](/Users/mattfaltyn/Desktop/hypertrial_trilemma/trading/market_watch/app/pages): KISS overview, implementation, signals, market-watch, and ticker detail views
- [config/](/Users/mattfaltyn/Desktop/hypertrial_trilemma/trading/market_watch/config): YAML methodology, sleeve mappings, and thresholds
- [tests/](/Users/mattfaltyn/Desktop/hypertrial_trilemma/trading/market_watch/tests): cache, KISS services, signals, watchlist support, and page rendering tests
