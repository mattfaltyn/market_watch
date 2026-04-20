# Bitcoin Market Watch

Local-first **BTC-USD** dashboard powered by **Plotly Dash**, **dash-mantine-components**, and **Yahoo Finance** via **`yfinance`**. One page: current price, daily change, moving-average context, a range-selectable price chart (with optional 20D/50D overlays), key return and risk stats, volume, and range/drawdown context.

## Features

- Single symbol: **BTC-USD** (daily closes)
- File-backed cache under `.cache/`
- Configurable default chart range and moving-average windows (`config/settings.yaml`)
- Manual refresh (invalidates market cache for a fresh Yahoo pull)

## Run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
python -m app.main
```

Open `http://127.0.0.1:8050`.

## Tests

```bash
.venv/bin/pytest
```

Parallel workers and **100% branch coverage** on `app/` are enforced via `pyproject.toml`.

## Documentation

| Doc | Description |
|-----|-------------|
| [AGENTS.md](AGENTS.md) | Repo map, setup, verification |
| [docs/architecture.md](docs/architecture.md) | Bootstrap, data, and UI layout |
| [docs/testing.md](docs/testing.md) | Pytest and coverage |
