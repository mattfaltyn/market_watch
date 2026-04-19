# Development

## Environment

- **Python:** 3.11+ ([`pyproject.toml`](../pyproject.toml) `requires-python`).
- **Create venv and install:**

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e '.[dev]'
```

## Run the app

```bash
python -m app.main
```

Open `http://127.0.0.1:8050`.

## Tests

Run the full suite before claiming green builds:

```bash
.venv/bin/pytest
```

[`pyproject.toml`](../pyproject.toml) sets `testpaths = ["tests"]`, runs tests in **parallel** (`pytest-xdist` `-n auto`), and enforces **100% branch coverage** of `app/` via `pytest-cov`. Details: [testing.md](testing.md).

You may see **DeprecationWarning** from `dash_table.DataTable`; that is expected until the UI migrates.

Use **`-n0`** for a single-process run when debugging (see [testing.md](testing.md)).

Optional smoke import:

```bash
.venv/bin/python -c "from app.main import create_app; app=create_app(); print(type(app).__name__)"
```

## Code style

- Match neighboring modules: typing style, dataclasses in [`app/models.py`](../app/models.py), service patterns in [`app/services/`](../app/services/).
- Prefer **extending** existing services and [`MarketDataClient`](../app/data/yfinance_client.py) over parallel data layers.
- Keep changes **scoped** to the task; avoid drive-by refactors and unrelated formatting churn.

## Tests and fakes

Integration-style tests use **fake clients** that implement the subset of `MarketDataClient` methods each service needs (see [`tests/test_regime_history.py`](../tests/test_regime_history.py), [`tests/test_pages.py`](../tests/test_pages.py)). Follow that pattern for new service tests.

## Documentation

- Product overview: [README.md](../README.md).
- Agent-oriented checklist: [AGENTS.md](../AGENTS.md).
- Deeper topics: this `docs/` directory.
