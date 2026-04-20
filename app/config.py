from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


ROOT_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = ROOT_DIR / "config"


@dataclass(frozen=True)
class DashboardConfig:
    symbol: str
    default_range: str
    moving_averages: tuple[int, ...]
    refresh_interval_seconds: int


@dataclass(frozen=True)
class CacheConfig:
    default_ttl_seconds: int
    market_ttl_seconds: int


@dataclass(frozen=True)
class AppConfig:
    dashboard: DashboardConfig
    cache: CacheConfig


def _load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Expected mapping in {path}")
    return data


def load_config() -> AppConfig:
    settings = _load_yaml(CONFIG_DIR / "settings.yaml")
    dash = settings.get("dashboard") or {}
    cache = settings.get("cache") or {}
    ma_raw = dash.get("moving_averages") or (20, 50, 200)
    moving_averages = tuple(int(x) for x in ma_raw)
    return AppConfig(
        dashboard=DashboardConfig(
            symbol=str(dash.get("symbol", "BTC-USD")),
            default_range=str(dash.get("default_range", "90D")),
            moving_averages=moving_averages,
            refresh_interval_seconds=int(dash.get("refresh_interval_seconds", 0)),
        ),
        cache=CacheConfig(
            default_ttl_seconds=int(cache.get("default_ttl_seconds", 900)),
            market_ttl_seconds=int(cache.get("market_ttl_seconds", 900)),
        ),
    )
