# Data and caching

## defeatbeta-api

The app depends on **`defeatbeta-api`** for market and treasury data. Initial loads and cache misses require **network access** to the library’s upstream dataset behavior (see package documentation).

If calls fail, callbacks in [`app/main.py`](../app/main.py) surface [`fatal_error_page`](../app/components/ui.py) with guidance rather than a blank page.

## File cache

- **Location:** `<repo_root>/.cache/` — see `FileCache(ROOT_DIR / ".cache", ...)` in [`app/main.py`](../app/main.py).
- **Mechanism:** [`FileCache.get_or_set`](../app/data/cache.py) pickles payloads with a timestamp; TTL is per-call from [`CachePolicy`](../app/data/defeatbeta_client.py).
- **Keys:** Built in [`DefeatBetaClient._safe_cached_frame`](../app/data/defeatbeta_client.py). Price series use `"{symbol}_price"` when no override applies, or `"{symbol}_price__via_{fetch_symbol}"` when `price_fetch_overrides` redirects the fetch ticker (avoids reusing an empty cache entry under the old key).

## Refresh behavior

- **`refresh-state` store:** Incrementing refresh (via the refresh control wired to `refresh-button`) sets `force_refresh=True` on the next route evaluation when the trigger is the refresh store.
- Use refresh after config or override changes if you suspect stale pickles.

## Normalization

[`DefeatBetaClient._normalize_frame`](../app/data/defeatbeta_client.py) lowercases column names and parses date columns so downstream code can rely on `report_date`, `close`, etc.

## What not to commit

Do not commit `.cache/` contents, API secrets, or `.env` files. `.cache` and `.venv` belong in `.gitignore` / `.cursorignore` for local use only.
