# AGENTS.md

Guidance for coding agents and contributors working on **market_watch**.

## Project summary

Local-first **KISS regime and market-indicators** dashboard built with **Plotly Dash**, **dash-mantine-components**, and **`yfinance`** (Yahoo Finance). The home experience is regime-first (Overview: hero summary, quadrant, transitions, confirmation assets, indicator tape). Routes: `/`, `/markets`, `/watchlist`, `/ticker/<symbol>` (see [`docs/routing-and-pages.md`](docs/routing-and-pages.md)).

## Repository map

| Path | Purpose |
|------|---------|
| [`app/main.py`](app/main.py) | Dash app, `CONFIG` / `CLIENT` / `CACHE` singletons; callbacks delegate to [`app/routing.py`](app/routing.py) |
| [`app/routing.py`](app/routing.py) | `dispatch_page`, `dispatch_page_safe`, `refresh_state_payload` (unit-tested; Dash callbacks in `main` are thin wrappers) |
| [`app/config.py`](app/config.py) | Load `config/settings.yaml` → `AppConfig` |
| [`app/models.py`](app/models.py) | Shared dataclasses |
| [`app/components/`](app/components/) | Theme, layout, primitives, charts, tables, `ui.py` re-exports |
| [`app/pages/`](app/pages/) | Per-route layout builders (overview, markets, watchlist, ticker) |
| [`app/services/`](app/services/) | Regime, `regime_frame`, regime history, VAMS, market, watchlist, signals |
| [`app/data/`](app/data/) | `FileCache`, [`MarketDataClient`](app/data/yfinance_client.py) (Yahoo Finance) |
| [`config/settings.yaml`](config/settings.yaml) | Methodology, symbols, TTLs |
| [`tests/`](tests/) | Pytest suite (fakes for `MarketDataClient`-shaped clients) |
| [`docs/`](docs/) | Architecture, configuration, caching, development, routing |

## Setup and run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
python -m app.main
```

Open `http://127.0.0.1:8050`.

## Verification

Before stating that tests pass, run:

```bash
.venv/bin/pytest
```

The default pytest invocation runs workers in parallel and enforces **100% branch coverage** on `app/`. See [`docs/testing.md`](docs/testing.md) for `-n0`, HTML coverage reports, and exclusions.

`dash_table.DataTable` deprecation warnings are expected. Do not claim full green without running the suite.

## Configuration

- Primary file: [`config/settings.yaml`](config/settings.yaml).
- Details: [`docs/configuration.md`](docs/configuration.md).
- **Treasury short end:** `bc2_year` in the client uses Yahoo’s **5Y** index (`^FVX`) as a stand-in for a 2Y series; see [`docs/data-and-caching.md`](docs/data-and-caching.md).

## Coding expectations

- **Python 3.11+**; match existing typing and module layout.
- **Scope:** Change only what the task requires; no unrelated refactors.
- **Data access:** Use `MarketDataClient` and existing services; avoid ad-hoc duplicate fetch logic.
- **UI:** Prefer [`app/components/ui.py`](app/components/ui.py); keep the visual-first product style.

## Do not

- Commit secrets, `.env`, or `.cache/` blobs.
- Assume `get_prices(symbol)` always returns non-empty upstream frames.
- Add large generated artifacts or lockfiles unless the task explicitly requires them.

## Common tasks

| Task | Where to edit |
|------|----------------|
| New route or behavior branch | [`app/main.py`](app/main.py) callback + new or existing [`app/pages/`](app/pages/) |
| Regime / replay / overview data | [`app/services/regime_history.py`](app/services/regime_history.py), [`app/services/kiss_regime.py`](app/services/kiss_regime.py) |
| VAMS math | [`app/services/vams.py`](app/services/vams.py) |
| New config knobs | [`config/settings.yaml`](config/settings.yaml) + [`app/config.py`](app/config.py) if exposing properties |
| Yahoo / cache integration | [`app/data/yfinance_client.py`](app/data/yfinance_client.py) |
| Tests | [`tests/`](tests/) — mirror fake-client patterns in `test_regime_history.py` / `test_pages.py` |

## Further reading

- [README.md](README.md) — product overview and quick start  
- [docs/README.md](docs/README.md) — documentation index  
- [docs/testing.md](docs/testing.md) — pytest parallelism, branch coverage, debugging  
