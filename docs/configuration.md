# Configuration

## Source file

All runtime methodology and TTLs are loaded from [`config/settings.yaml`](../config/settings.yaml) via [`load_config()`](../app/config.py) into the frozen `AppConfig` dataclass.

## Top-level sections

### `kiss`

| Key | Purpose |
|-----|---------|
| `sleeves` | Symbol map: `equity`, `fixed_income`, `bitcoin`, `cash` — used for VAMS confirmation assets and allowed `/ticker/<symbol>` drill-downs. |
| `base_weights` | Baseline sleeve weights (KISS methodology; retained in YAML). |
| `regime_rules` | Per-regime target weights (methodology reference). |
| `vams_multipliers` | Bullish / neutral / bearish multipliers for VAMS confirmation scoring. |
| `regime_inputs` | `weak_score_threshold`, nested `growth` and `inflation` proxy symbol overrides (e.g. `equity_trend_symbol`, `yield_symbol`). |
| `market_watch_symbols` | List of tickers for market snapshot, overview indicator tape, and the Markets page (`/markets`). |

### `alert_thresholds`

Used by VAMS (`vams_bullish_threshold`, `vams_bearish_threshold`, `volatility_high_threshold`) and alerting (`large_move_1d`, `valuation_industry_gap`). See [`app/services/vams.py`](../app/services/vams.py) and [`app/services/signals.py`](../app/services/signals.py).

### `chart_windows`

`short_days`, `medium_days`, `long_days` — referenced by methodology docs; align changes with services that hard-code windows (e.g. 50-day trends) if you extend config usage.

### `cache`

TTLs (seconds) passed into [`CachePolicy`](../app/data/yfinance_client.py) in [`app/main.py`](../app/main.py): `default_ttl_seconds`, `market_ttl_seconds`, `fundamentals_ttl_seconds`, `news_ttl_seconds`.

## Symbols and Yahoo Finance

- **Logical** symbols in YAML (e.g. `AGG`, `BTC-USD`) are passed directly to `yfinance` as tickers.
- [`MarketDataClient.get_prices`](../app/data/yfinance_client.py) shapes OHLCV into `report_date`, `close`, etc. [`last_price_source`](../app/data/yfinance_client.py) is `yfinance` when a series loads successfully.
- **`KissRegime.unavailable_components`** lists regime proxy inputs that had no usable data (excluded from composite means); warnings surface on the Overview page via `RegimeOverviewSnapshot.warnings`.

## `AppConfig` properties

[`app/config.py`](../app/config.py) exposes `sleeves`, `regime_inputs`, `market_watch_symbols`, `sleeve_symbols`, etc., with consistent string normalization where applicable.
