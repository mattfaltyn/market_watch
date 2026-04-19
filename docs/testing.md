# Testing and coverage

## Default command

From the repo root with the project venv active:

```bash
.venv/bin/pytest
```

[`pyproject.toml`](../pyproject.toml) configures:

- **`pytest-xdist`** with **`-n auto`**: tests run in parallel across available logical CPUs.
- **`pytest-cov`** with **`--cov-branch`**: line and **branch** coverage are measured for the `app` package.
- **`fail_under = 100`**: the run fails unless total coverage (including branches) is **100%**.

Terminal output includes a per-file table with missing lines when something is not covered.

## HTML report

For a navigable report (useful when debugging gaps):

```bash
.venv/bin/pytest --cov=app --cov-branch --cov-report=html
open htmlcov/index.html   # macOS
```

## Single-process / debugging

Parallel runs can make breakpoints awkward. Disable xdist for one run:

```bash
.venv/bin/pytest -n0
```

Combine with `-x` or `--pdb` as needed.

## What is excluded from coverage

- **`app/main.py`**: The Dash callback wrappers (`refresh_data`, `route`) are thin delegates to [`app/routing.py`](../app/routing.py); they are marked with `# pragma: no cover`. Behavior is covered by tests on `refresh_state_payload`, `dispatch_page`, and `dispatch_page_safe`.
- **`if __name__ == "__main__"`** in `main.py`: local `app.run()` entrypoint is not executed in CI/tests (`# pragma: no cover`).

Avoid adding broad `omit` globs in coverage config; prefer tests or a short, justified pragma on glue-only lines.

## Fakes and network

Unit tests use **fake clients** that implement only the methods the code under test calls (see [`tests/routing_fake.py`](../tests/routing_fake.py), [`tests/test_regime_history.py`](../tests/test_regime_history.py)). Avoid live network except where explicitly marked or isolated.

## Deprecation warnings

`dash_table.DataTable` deprecation warnings during tests are expected until the UI migrates (see [`docs/development.md`](development.md)).
