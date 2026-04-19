from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal

import pandas as pd


@dataclass(frozen=True)
class MetricCard:
    label: str
    value: str
    delta: str | None = None
    tone: str = "neutral"
    variant: str = "kpi"
    icon: str | None = None
    sparkline: list[float] | None = None
    emphasis: str = "normal"


@dataclass(frozen=True)
class VisualChangeEvent:
    label: str
    value: str
    tone: str = "neutral"
    caption: str | None = None


@dataclass(frozen=True)
class SignalTransition:
    label: str
    prior_state: str
    current_state: str
    transition_date: datetime | None
    age_days: int | None
    caption: str


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
    source: str | None = None


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
class KissRegime:
    regime: Literal["goldilocks", "reflation", "inflation", "deflation"]
    regime_strength: float
    hybrid_label: str | None
    growth_direction: Literal["up", "down"]
    inflation_direction: Literal["up", "down"]
    component_scores: dict[str, float | None]
    as_of: datetime | None
    reasons: list[str] = field(default_factory=list)
    unavailable_components: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class RegimeHistoryPoint:
    date: datetime | None
    regime: Literal["goldilocks", "reflation", "inflation", "deflation"]
    growth_score: float
    inflation_score: float
    regime_strength: float


@dataclass(frozen=True)
class IndicatorSnapshot:
    symbol: str
    latest_value: float | None
    change_1d: float | None
    change_5d: float | None
    change_1m: float | None
    trend_state: str
    volatility: float | None
    as_of: datetime | None
    source: str | None = None


@dataclass(frozen=True)
class ConfirmationSnapshot:
    symbol: str
    role_label: str
    state: Literal["bullish", "neutral", "bearish"]
    score: float
    trend: float | None
    momentum: float | None
    volatility: float | None
    last_transition: SignalTransition | None
    as_of: datetime | None


@dataclass(frozen=True)
class VamsSignal:
    symbol: str
    state: Literal["bullish", "neutral", "bearish"]
    score: float
    volatility: float | None
    trend: float | None
    momentum: float | None
    as_of: datetime | None
    reasons: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class VamsHistoryPoint:
    date: datetime | None
    state: Literal["bullish", "neutral", "bearish"]
    score: float
    trend: float | None
    momentum: float | None
    volatility: float | None


@dataclass(frozen=True)
class SignalChange:
    symbol: str
    field: str
    old_value: str
    new_value: str
    message: str


@dataclass(frozen=True)
class SleeveAllocation:
    name: str
    symbol: str
    base_weight: float
    target_weight: float
    actual_weight: float
    vams_state: str
    vams_multiplier: float
    regime_rule_applied: str
    delta_from_prior: float | None
    notes: str = ""


@dataclass(frozen=True)
class KissPortfolioSnapshot:
    regime: KissRegime
    sleeves: list[SleeveAllocation]
    cash_symbol: str
    cash_weight: float
    gross_exposure: float
    summary_text: str
    implementation_text: str
    signal_changes: list[SignalChange]
    as_of: datetime | None


@dataclass(frozen=True)
class RegimeOverviewSnapshot:
    regime: KissRegime
    regime_history: list[RegimeHistoryPoint]
    indicators: list[IndicatorSnapshot]
    confirmations: list[ConfirmationSnapshot]
    transitions: list[SignalTransition]
    as_of: datetime | None
    summary_text: str
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class TickerDetailBundle:
    symbol: str
    info: pd.DataFrame
    price: pd.DataFrame
    valuation: dict[str, pd.DataFrame]
    quality: dict[str, pd.DataFrame]
    growth: dict[str, pd.DataFrame]
    news: pd.DataFrame
    calendar: pd.DataFrame
    alerts: list[AlertFlag] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    role_label: str | None = None


@dataclass(frozen=True)
class DataResult:
    data: Any
    errors: list[str] = field(default_factory=list)
