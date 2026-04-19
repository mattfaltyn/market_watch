# Data and caching

## Yahoo Finance (`yfinance`)

The app loads market, treasury, and fundamental-style data through **`yfinance`** (Yahoo Finance), wrapped by [`MarketDataClient`](../app/data/yfinance_client.py). Initial loads and cache misses require **network access** to Yahoo’s endpoints (subject to Yahoo rate limits and availability).

If calls fail, callbacks in [`app/main.py`](../app/main.py) surface [`fatal_error_page`](../app/components/ui.py) with guidance rather than a blank page.

### Treasury yields

[`MarketDataClient.get_treasury_yields`](../app/data/yfinance_client.py) merges constant-maturity index proxies:

- `bc10_year` ← `^TNX` (10Y, percent quote ÷ 100 → decimal yield)
- `bc30_year` ← `^TYX` (30Y)
- `bc2_year` ← `^FVX` (**5Y** Yahoo proxy used in place of a dedicated 2Y series). The UI still labels spreads as **10Y–2Y**; interpret the short end as this proxy.

If calls fail, [`build_rates_snapshot`](../app/services/market_snapshot.py) returns empty rate fields.

### Ticker detail scope

The `/ticker/<symbol>` view uses Yahoo for price, valuation/quality/growth metrics derived from `info` and `quarterly_income_stmt`, news, and the earnings calendar. **SEC filings, earnings transcripts, and revenue segment/geography breakdowns are not provided** by this client and are omitted from the UI.

## File cache

- **Location:** `<repo_root>/.cache/` — see `FileCache(ROOT_DIR / ".cache", ...)` in [`app/main.py`](../app/main.py).
- **Mechanism:** [`FileCache.get_or_set`](../app/data/cache.py) pickles payloads with a timestamp; TTL is per-call from [`CachePolicy`](../app/data/yfinance_client.py).
- **Keys:** Built in [`MarketDataClient._safe_cached_frame`](../app/data/yfinance_client.py). Examples: `"{symbol}_price__src_yfinance"`, `"treasury_yields"`, `"sp500_history"`, `"{symbol}_info"`, `"{symbol}_news"`.

## Refresh behavior

- **`refresh-state` store:** Incrementing refresh (via the refresh control wired to `refresh-button`) sets `force_refresh=True` on the next route evaluation when the trigger is the refresh store.
- Use refresh after config changes if you suspect stale pickles.

## Normalization

[`MarketDataClient._normalize_frame`](../app/data/yfinance_client.py) lowercases column names and parses date columns so downstream code can rely on `report_date`, `close`, etc.

## What not to commit

Do not commit `.cache/` contents, API secrets, or `.env` files. `.cache` and `.venv` belong in `.gitignore` / `.cursorignore` for local use only.
