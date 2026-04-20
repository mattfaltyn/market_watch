# Testing and coverage

## Command

From the repo root with the project venv:

```bash
.venv/bin/pytest
```

[`pyproject.toml`](../pyproject.toml) enables `pytest-xdist` (`-n auto`), `pytest-cov` with `--cov-branch`, and `fail_under = 100` for **line and branch** coverage on the `app` package.

## Single-process debugging

```bash
.venv/bin/pytest -n0
```

## HTML coverage report

```bash
.venv/bin/pytest --cov=app --cov-branch --cov-report=html
open htmlcov/index.html
```

## Notes

- Dash callback entrypoints in [`app/main.py`](../app/main.py) use `# pragma: no cover`; behavior is covered via [`run_dashboard_fetch()`](../app/dashboard.py) and component tests.
- Unit tests monkeypatch `yfinance` so tests do not hit the live network.
