from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class PriceStats:
    ret_7d: float | None
    ret_30d: float | None
    ret_90d: float | None
    ret_ytd: float | None
    ret_1y: float | None
    ath_price: float | None
    dist_from_ath_pct: float | None
    vol_30d_ann: float | None
    ma20_state: str | None
    ma50_state: str | None
    ma200_state: str | None
    drawdown_from_peak_pct: float | None
    high_52w: float | None
    low_52w: float | None
    avg_volume_30d: float | None
    latest_volume: float | None


@dataclass(frozen=True)
class ChartSeries:
    report_dates: list[datetime]
    close: list[float]
    ma20: list[float | None]
    ma50: list[float | None]
    volume: list[float]


@dataclass(frozen=True)
class BitcoinSnapshot:
    symbol: str
    as_of: datetime | None
    latest_price: float | None
    change_1d_pct: float | None
    change_1d_abs: float | None
    ma_summary_chip: str
    stats: PriceStats
    chart: ChartSeries
    range_key: str


@dataclass(frozen=True)
class DataResult:
    data: Any
    errors: list[str] = field(default_factory=list)
