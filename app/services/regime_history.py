from __future__ import annotations

import pandas as pd

from app.models import ConfirmationSnapshot, IndicatorSnapshot, KissRegime, RegimeHistoryPoint, RegimeOverviewSnapshot, SignalTransition
from app.services.kiss_regime import get_kiss_regime
from app.services.market_snapshot import build_rates_snapshot
from app.services.regime_frame import (
    _classify_regime,
    _close_series,
    _ratio_trend_series,
    _trend_series,
    _yield_trend_series,
    build_regime_composite_frame,
)
from app.services.vams import get_vams_signal_history, get_vams_signals


def build_regime_history(client, config, force_refresh: bool = False) -> list[RegimeHistoryPoint]:
    frame = build_regime_composite_frame(client, config, force_refresh=force_refresh)
    return [
        RegimeHistoryPoint(
            date=row["report_date"].to_pydatetime() if isinstance(row["report_date"], pd.Timestamp) else row["report_date"],
            regime=row["regime"],
            growth_score=float(row["growth_score"]),
            inflation_score=float(row["inflation_score"]),
            regime_strength=float(row["regime_strength"]),
        )
        for _, row in frame.iterrows()
    ]


def _latest_transition(label: str, states: list[str], dates: list[pd.Timestamp]) -> SignalTransition | None:
    paired = [(state, date) for state, date in zip(states, dates) if date is not None]
    if not paired:
        return None
    filtered_states = [state for state, _ in paired]
    filtered_dates = [date for _, date in paired]
    current = filtered_states[-1]
    for index in range(len(filtered_states) - 1, 0, -1):
        if filtered_states[index] != filtered_states[index - 1]:
            transition_date = filtered_dates[index]
            age = len(filtered_states) - 1 - index
            return SignalTransition(
                label=label,
                prior_state=filtered_states[index - 1],
                current_state=current,
                transition_date=transition_date.to_pydatetime() if isinstance(transition_date, pd.Timestamp) else transition_date,
                age_days=age,
                caption=f"{label} changed {filtered_states[index - 1]} -> {current} {age} trading days ago.",
            )
    last_date = filtered_dates[-1]
    return SignalTransition(
        label=label,
        prior_state=current,
        current_state=current,
        transition_date=last_date.to_pydatetime() if isinstance(last_date, pd.Timestamp) else last_date,
        age_days=len(filtered_states) - 1,
        caption=f"{label} has remained {current} for {len(filtered_states) - 1} trading days.",
    )


def _indicator_from_price(symbol: str, frame: pd.DataFrame, source: str | None = None) -> IndicatorSnapshot:
    if frame.empty or "close" not in frame.columns:
        return IndicatorSnapshot(symbol, None, None, None, None, "unavailable", None, None, source)
    ordered = frame.sort_values("report_date")
    close = pd.to_numeric(ordered["close"], errors="coerce").dropna()
    if close.empty:
        return IndicatorSnapshot(symbol, None, None, None, None, "unavailable", None, None, source)
    returns = close.pct_change().dropna()
    trend = "above_50d" if len(close) >= 50 and close.iloc[-1] >= close.rolling(50).mean().iloc[-1] else "below_50d"
    return IndicatorSnapshot(
        symbol=symbol,
        latest_value=float(close.iloc[-1]),
        change_1d=float(close.iloc[-1] / close.iloc[-2] - 1.0) if len(close) > 1 else None,
        change_5d=float(close.iloc[-1] / close.iloc[-6] - 1.0) if len(close) > 5 else None,
        change_1m=float(close.iloc[-1] / close.iloc[-22] - 1.0) if len(close) > 21 else None,
        trend_state=trend,
        volatility=float(returns.tail(20).std() * (252 ** 0.5)) if len(returns) >= 20 else None,
        as_of=ordered["report_date"].max().to_pydatetime(),
        source=source,
    )


def _build_indicator_snapshots(client, config, force_refresh: bool = False) -> list[IndicatorSnapshot]:
    symbols = config.market_watch_symbols
    indicators = []
    for symbol in symbols:
        result = client.get_prices(symbol, force_refresh=force_refresh)
        src = client.last_price_source(symbol) if hasattr(client, "last_price_source") else None
        indicators.append(_indicator_from_price(symbol, result.data, src))
    rates = build_rates_snapshot(client, force_refresh=force_refresh)
    indicators.append(
        IndicatorSnapshot("10Y", rates.y10, None, rates.change_10y_5d, rates.change_10y_1m, "up" if (rates.change_10y_1m or 0) >= 0 else "down", None, rates.as_of)
    )
    spread = rates.spread_10y_short_proxy
    indicators.append(
        IndicatorSnapshot(
            "10Y-5Y",
            spread,
            None,
            None,
            None,
            "steepening" if (spread or 0) >= 0 else "inverted",
            None,
            rates.as_of,
        )
    )
    return indicators


def build_regime_overview_snapshot(client, config, force_refresh: bool = False) -> RegimeOverviewSnapshot:
    regime = get_kiss_regime(client, config, force_refresh=force_refresh)
    regime_history = build_regime_history(client, config, force_refresh=force_refresh)
    indicators = _build_indicator_snapshots(client, config, force_refresh=force_refresh)
    confirmation_symbols = [config.sleeves["equity"], config.sleeves["fixed_income"], config.sleeves["bitcoin"]]
    vams_signals = get_vams_signals(client, confirmation_symbols, config.alert_thresholds, force_refresh=force_refresh)
    vams_history = get_vams_signal_history(client, confirmation_symbols, config.alert_thresholds, force_refresh=force_refresh)

    transitions: list[SignalTransition] = []
    if regime_history:
        transitions.append(
            _latest_transition(
                "Regime",
                [point.regime for point in regime_history],
                [pd.Timestamp(point.date) for point in regime_history if point.date is not None],
            )
        )
    confirmations: list[ConfirmationSnapshot] = []
    role_labels = {
        config.sleeves["equity"]: "Equity confirmation",
        config.sleeves["fixed_income"]: "Bond confirmation",
        config.sleeves["bitcoin"]: "Risk appetite confirmation",
    }
    for symbol in confirmation_symbols:
        history_points = vams_history.get(symbol, [])
        transition = _latest_transition(
            symbol,
            [point.state for point in history_points],
            [pd.Timestamp(point.date) for point in history_points if point.date is not None],
        )
        if transition is not None:
            transitions.append(transition)
        signal = vams_signals[symbol]
        confirmations.append(
            ConfirmationSnapshot(
                symbol=symbol,
                role_label=role_labels[symbol],
                state=signal.state,
                score=signal.score,
                trend=signal.trend,
                momentum=signal.momentum,
                volatility=signal.volatility,
                last_transition=transition,
                as_of=signal.as_of,
            )
        )

    cleaned_transitions = [transition for transition in transitions if transition is not None]
    summary_text = f"{regime.regime.title()} regime with growth {regime.growth_direction} and inflation {regime.inflation_direction}."
    as_of_candidates = [regime.as_of] + [indicator.as_of for indicator in indicators if indicator.as_of is not None]
    as_of = max((candidate for candidate in as_of_candidates if candidate is not None), default=None)
    warnings: list[str] = []
    if regime.unavailable_components:
        warnings.append(
            f"Some regime inputs had no data (excluded from composite): {', '.join(regime.unavailable_components)}."
        )
    return RegimeOverviewSnapshot(
        regime=regime,
        regime_history=regime_history,
        indicators=indicators,
        confirmations=confirmations,
        transitions=cleaned_transitions,
        as_of=as_of,
        summary_text=summary_text,
        warnings=warnings,
    )
