from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


ROOT_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = ROOT_DIR / "config"


@dataclass(frozen=True)
class AppConfig:
    kiss: dict[str, Any]
    chart_windows: dict[str, int]
    cache: dict[str, Any]
    alert_thresholds: dict[str, Any]

    @property
    def sleeves(self) -> dict[str, str]:
        return self.kiss.get("sleeves", {})

    @property
    def base_weights(self) -> dict[str, float]:
        return self.kiss.get("base_weights", {})

    @property
    def regime_rules(self) -> dict[str, dict[str, float]]:
        return self.kiss.get("regime_rules", {})

    @property
    def vams_multipliers(self) -> dict[str, float]:
        return self.kiss.get("vams_multipliers", {})

    @property
    def regime_inputs(self) -> dict[str, Any]:
        return self.kiss.get("regime_inputs", {})

    @property
    def market_watch_symbols(self) -> list[str]:
        return [str(symbol).upper() for symbol in self.kiss.get("market_watch_symbols", [])]

    @property
    def price_fetch_overrides(self) -> dict[str, str]:
        """Map logical symbols (UI / methodology) to defeatbeta tickers when the primary has no series."""
        raw = self.kiss.get("price_fetch_overrides") or {}
        return {str(k).strip(): str(v).strip() for k, v in raw.items()}

    @property
    def sleeve_symbols(self) -> list[str]:
        return [str(symbol).upper() for symbol in self.sleeves.values()]


def _load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Expected mapping in {path}")
    return data


def load_config() -> AppConfig:
    settings = _load_yaml(CONFIG_DIR / "settings.yaml")
    return AppConfig(
        kiss=settings.get("kiss", {}),
        chart_windows=settings.get("chart_windows", {}),
        cache=settings.get("cache", {}),
        alert_thresholds=settings.get("alert_thresholds", {}),
    )
