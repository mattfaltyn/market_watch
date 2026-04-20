# AGENTS.md

Guidance for coding agents and contributors working on **market_watch**.

## Project summary

Local-first **Bitcoin (BTC-USD)** dashboard built with **Plotly Dash**, **dash-mantine-components**, and **`yfinance`**. Single route: `/`. Styling lives in [`assets/theme.css`](assets/theme.css); Mantine/Plotly tokens align with [`app/components/theme.py`](app/components/theme.py).

## Repository map

| Path | Purpose |
|------|---------|
| [`app/main.py`](app/main.py) | `create_app()`, `CONFIG` / `CLIENT` / `CACHE`, Dash callbacks |
| [`app/dashboard.py`](app/dashboard.py) | Layout factory, metrics formatting, Plotly figures, `run_dashboard_fetch()` |
| [`app/config.py`](app/config.py) | `load_config()` → `AppConfig` |
| [`app/models.py`](app/models.py) | `BitcoinSnapshot`, `PriceStats`, `ChartSeries`, `DataResult` |
| [`app/metrics.py`](app/metrics.py) | Returns, ATH, vol, chart slices, MA helpers |
| [`app/data/bitcoin_client.py`](app/data/bitcoin_client.py) | Cached BTC-USD history via `yfinance` |
| [`app/data/cache.py`](app/data/cache.py) | `FileCache` |
| [`config/settings.yaml`](config/settings.yaml) | Symbol, ranges, TTLs |
| [`tests/`](tests/) | Pytest (monkeypatched Yahoo) |
| [`docs/`](docs/) | Architecture and testing |

## Setup and run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
python -m app.main
```

Open `http://127.0.0.1:8050`.

## Verification

```bash
.venv/bin/pytest
```

Do not claim tests pass without this command. See [`docs/testing.md`](docs/testing.md).

## Configuration

Edit [`config/settings.yaml`](config/settings.yaml) (symbol `BTC-USD`, default chart range, MA windows, cache TTLs).

## Coding expectations

- **Python 3.11+**; match existing typing and layout.
- **Scope:** change only what the task requires.
- **Data:** use `BitcoinDataClient` and `FileCache`; avoid duplicate fetch layers.
- **UI:** compose in [`app/dashboard.py`](app/dashboard.py); keep tokens in CSS / `theme.py`.

## Do not

- Commit secrets, `.env`, or `.cache/` blobs.
- Assume Yahoo history is always non-empty.

## Common tasks

| Task | Where to edit |
|------|----------------|
| Metrics or chart windows | [`app/metrics.py`](app/metrics.py), [`config/settings.yaml`](config/settings.yaml) |
| Layout / copy | [`app/dashboard.py`](app/dashboard.py), [`assets/theme.css`](assets/theme.css) |
| Cache TTL | [`config/settings.yaml`](config/settings.yaml) |
| Tests | [`tests/`](tests/) |

## Further reading

- [README.md](README.md) — overview and quick start  
- [docs/README.md](docs/README.md) — doc index  
