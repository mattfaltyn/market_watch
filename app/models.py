from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class MetricCard:
    label: str
    value: str
    delta: str | None = None
    tone: str = "neutral"
    variant: str = "kpi"


@dataclass(frozen=True)
class MarketIndexSnapshot:
    symbol: str
    close: float | None
    return_1d: float | None
    return_5d: float | None
    return_1m: float | None
    realized_vol_20d: float | None
    ma20_state: str
    ma50_state: str
    ma200_state: str
    as_of: datetime | None


@dataclass(frozen=True)
class MarketSnapshot:
    indices: list[MarketIndexSnapshot]
    positive_participation_ratio: float
    as_of: datetime | None


@dataclass(frozen=True)
class RatesSnapshot:
    as_of: datetime | None
    y2: float | None
    y10: float | None
    y30: float | None
    spread_10y_2y: float | None
    change_10y_5d: float | None
    change_10y_1m: float | None


@dataclass(frozen=True)
class RegimeSignal:
    regime: str
    score: int
    reasons: list[str]


@dataclass(frozen=True)
class AlertFlag:
    symbol: str
    category: str
    message: str
    severity: str


@dataclass(frozen=True)
class TickerDetailBundle:
    symbol: str
    info: pd.DataFrame
    price: pd.DataFrame
    valuation: dict[str, pd.DataFrame]
    quality: dict[str, pd.DataFrame]
    growth: dict[str, pd.DataFrame]
    news: pd.DataFrame
    filings: pd.DataFrame
    calendar: pd.DataFrame
    revenue_breakdown: dict[str, pd.DataFrame]
    transcripts: pd.DataFrame
    alerts: list[AlertFlag] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class DataResult:
    data: Any
    errors: list[str] = field(default_factory=list)
