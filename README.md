# market_watch

Local-first market dashboard built with Plotly Dash and `defeatbeta-api`.

## Run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
python -m app.main
```

Open `http://127.0.0.1:8050`.

## Notes

- The dashboard fetches live data through `defeatbeta-api`, so initial page loads require network access to the upstream dataset.
- If the upstream source is unavailable, the app now renders an in-app error state instead of a blank page.

## Structure

- `app/main.py`: Dash entrypoint and routing
- `app/data/`: cache and `defeatbeta-api` adapter
- `app/services/`: market, watchlist, and regime logic
- `app/pages/`: overview, watchlist, and ticker detail views
- `config/`: YAML watchlist and settings
- `tests/`: cache, signals, services, and page rendering tests
