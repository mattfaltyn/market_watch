# Configuration

## Source file

All runtime methodology and TTLs are loaded from [`config/settings.yaml`](../config/settings.yaml) via [`load_config()`](../app/config.py) into the frozen `AppConfig` dataclass.

## Top-level sections

### `kiss`

| Key | Purpose |
|-----|---------|
| `sleeves` | Symbol map: `equity`, `fixed_income`, `bitcoin`, `cash` — used for confirmation, `/implementation`, and allowed `/ticker/` symbols. |
| `base_weights` | Baseline weights for the legacy `/implementation` view. |
| `regime_rules` | Per-regime target weights for legacy portfolio construction. |
| `vams_multipliers` | Bullish / neutral / bearish multipliers for legacy allocation math. |
| `regime_inputs` | `weak_score_threshold`, nested `growth` and `inflation` proxy symbol overrides (e.g. `equity_trend_symbol`, `yield_symbol`). |
| `market_watch_symbols` | List of tickers for market snapshot, overview indicator tape, and `/market-watch`. |
| `price_fetch_overrides` | Map **logical** symbol → **defeatbeta** ticker when the primary symbol has no price series in the upstream dataset. Example: `AGG: TLT`, `BTC-USD: IBIT`. |

### `alert_thresholds`

Used by VAMS (`vams_bullish_threshold`, `vams_bearish_threshold`, `volatility_high_threshold`) and alerting (`large_move_1d`, `valuation_industry_gap`). See [`app/services/vams.py`](../app/services/vams.py) and [`app/services/signals.py`](../app/services/signals.py).

### `chart_windows`

`short_days`, `medium_days`, `long_days` — referenced by methodology docs; align changes with services that hard-code windows (e.g. 50-day trends) if you extend config usage.

### `cache`

TTLs (seconds) passed into [`CachePolicy`](../app/data/defeatbeta_client.py) in [`app/main.py`](../app/main.py): `default_ttl_seconds`, `market_ttl_seconds`, `fundamentals_ttl_seconds`, `news_ttl_seconds`, `filings_ttl_seconds`, `transcripts_ttl_seconds`.

## Logical vs fetch ticker

- **Logical** symbols appear in the UI, `RegimeOverviewSnapshot`, and YAML (`AGG`, `BTC-USD`).
- **Fetch** symbols are what `defeatbeta_api` `Ticker(...).price()` loads when an override exists.
- Do not assume every logical ETF or crypto pair exists in defeatbeta; verify or extend `price_fetch_overrides`.

## `AppConfig` properties

[`app/config.py`](../app/config.py) exposes `sleeves`, `regime_inputs`, `market_watch_symbols`, `price_fetch_overrides`, `sleeve_symbols`, etc., with consistent string normalization where applicable.
