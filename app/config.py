from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


ROOT_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = ROOT_DIR / "config"


@dataclass(frozen=True)
class AppConfig:
    benchmark: str
    watchlist: list[str]
    alert_thresholds: dict[str, Any]
    chart_windows: dict[str, int]
    cache: dict[str, Any]


def _load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Expected mapping in {path}")
    return data


def load_config() -> AppConfig:
    settings = _load_yaml(CONFIG_DIR / "settings.yaml")
    watchlist_data = _load_yaml(CONFIG_DIR / "watchlist.yaml")
    return AppConfig(
        benchmark=str(settings.get("benchmark", "SPY")).upper(),
        watchlist=[str(ticker).upper() for ticker in watchlist_data.get("tickers", [])],
        alert_thresholds=settings.get("alert_thresholds", {}),
        chart_windows=settings.get("chart_windows", {}),
        cache=settings.get("cache", {}),
    )
