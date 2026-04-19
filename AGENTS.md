# AGENTS.md

Guidance for coding agents and contributors working on **market_watch**.

## Project summary

Local-first **KISS regime and market-indicators** dashboard built with **Plotly Dash** and **`defeatbeta-api`**. The home experience is regime-first (quadrant, drivers, historical transitions, confirmation assets). Legacy portfolio implementation remains on `/implementation`.

## Repository map

| Path | Purpose |
|------|---------|
| [`app/main.py`](app/main.py) | Dash app, `CONFIG` / `CLIENT` / `CACHE` singletons; callbacks delegate to [`app/routing.py`](app/routing.py) |
| [`app/routing.py`](app/routing.py) | `dispatch_page`, `dispatch_page_safe`, `refresh_state_payload` (unit-tested; Dash callbacks in `main` are thin wrappers) |
| [`app/config.py`](app/config.py) | Load `config/settings.yaml` → `AppConfig` |
| [`app/models.py`](app/models.py) | Shared dataclasses |
| [`app/components/`](app/components/) | Reusable UI (`ui.py`, CSS constants) |
| [`app/pages/`](app/pages/) | Per-route layout builders |
| [`app/services/`](app/services/) | Regime, VAMS, regime history, portfolio, market, watchlist, signals |
| [`app/data/`](app/data/) | `FileCache`, `DefeatBetaClient` |
| [`config/settings.yaml`](config/settings.yaml) | Methodology, symbols, TTLs, `price_fetch_overrides` |
| [`tests/`](tests/) | Pytest suite (fakes for defeatbeta-shaped clients) |
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
- **Symbol coverage:** Not every logical ticker has a defeatbeta price series. Use `kiss.price_fetch_overrides` (see YAML) and [`docs/data-and-caching.md`](docs/data-and-caching.md).

## Coding expectations

- **Python 3.11+**; match existing typing and module layout.
- **Scope:** Change only what the task requires; no unrelated refactors.
- **Data access:** Use `DefeatBetaClient` and existing services; avoid ad-hoc duplicate fetch logic.
- **UI:** Prefer [`app/components/ui.py`](app/components/ui.py); keep the visual-first product style.

## Do not

- Commit secrets, `.env`, or `.cache/` blobs.
- Assume `get_prices(logical_symbol)` returns data without checking overrides / upstream coverage.
- Add large generated artifacts or lockfiles unless the task explicitly requires them.

## Common tasks

| Task | Where to edit |
|------|----------------|
| New route or behavior branch | [`app/main.py`](app/main.py) callback + new or existing [`app/pages/`](app/pages/) |
| Regime / replay / overview data | [`app/services/regime_history.py`](app/services/regime_history.py), [`app/services/kiss_regime.py`](app/services/kiss_regime.py) |
| VAMS math | [`app/services/vams.py`](app/services/vams.py) |
| Legacy allocation | [`app/services/kiss_portfolio.py`](app/services/kiss_portfolio.py), [`app/pages/implementation.py`](app/pages/implementation.py) |
| New config knobs | [`config/settings.yaml`](config/settings.yaml) + [`app/config.py`](app/config.py) if exposing properties |
| defeatbeta integration | [`app/data/defeatbeta_client.py`](app/data/defeatbeta_client.py) |
| Tests | [`tests/`](tests/) — mirror fake-client patterns in `test_regime_history.py` / `test_pages.py` |

## Further reading

- [README.md](README.md) — product overview and quick start  
- [docs/README.md](docs/README.md) — documentation index  
- [docs/testing.md](docs/testing.md) — pytest parallelism, branch coverage, debugging  
