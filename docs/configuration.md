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
| `price_fetch_overrides` | Optional map **logical** symbol → **defeatbeta** ticker when the primary symbol has no price series in defeatbeta. Usually empty: the app falls back to Yahoo Finance for missing logical symbols. |

### `alert_thresholds`

Used by VAMS (`vams_bullish_threshold`, `vams_bearish_threshold`, `volatility_high_threshold`) and alerting (`large_move_1d`, `valuation_industry_gap`). See [`app/services/vams.py`](../app/services/vams.py) and [`app/services/signals.py`](../app/services/signals.py).

### `chart_windows`

`short_days`, `medium_days`, `long_days` — referenced by methodology docs; align changes with services that hard-code windows (e.g. 50-day trends) if you extend config usage.

### `cache`

TTLs (seconds) passed into [`CachePolicy`](../app/data/defeatbeta_client.py) in [`app/main.py`](../app/main.py): `default_ttl_seconds`, `market_ttl_seconds`, `fundamentals_ttl_seconds`, `news_ttl_seconds`, `filings_ttl_seconds`, `transcripts_ttl_seconds`.

## Logical vs fetch ticker vs Yahoo fallback

- **Logical** symbols appear in the UI, `RegimeOverviewSnapshot`, and YAML (`AGG`, `BTC-USD`).
- **Defeatbeta fetch** uses `Ticker(logical).price()` unless `price_fetch_overrides` maps the logical symbol to another defeatbeta ticker.
- If defeatbeta returns an empty frame, **Yahoo Finance** (`yfinance`) fills the gap for the same logical symbol; see [`app/data/yfinance_client.py`](../app/data/yfinance_client.py).
- **`KissRegime.unavailable_components`** lists regime proxy inputs that had no usable data (excluded from composite means); warnings are merged into the regime/signals page error strip via `RegimeOverviewSnapshot.warnings`.

## `AppConfig` properties

[`app/config.py`](../app/config.py) exposes `sleeves`, `regime_inputs`, `market_watch_symbols`, `price_fetch_overrides`, `sleeve_symbols`, etc., with consistent string normalization where applicable.
