from __future__ import annotations

from app.models import KissPortfolioSnapshot, SignalChange, SleeveAllocation


_PRIOR_SNAPSHOT: KissPortfolioSnapshot | None = None


def _regime_rule_name(regime: str) -> str:
    return regime.replace("_", " ").title()


def build_kiss_portfolio_snapshot(regime, vams_signals: dict, config) -> KissPortfolioSnapshot:
    global _PRIOR_SNAPSHOT

    sleeves = []
    signal_changes: list[SignalChange] = []
    total_actual = 0.0
    target_rules = config.regime_rules.get(regime.regime, {})

    prior_sleeves = {s.symbol: s for s in _PRIOR_SNAPSHOT.sleeves} if _PRIOR_SNAPSHOT else {}

    for sleeve_name in ("equity", "fixed_income", "bitcoin"):
        symbol = config.sleeves[sleeve_name]
        base_weight = float(config.base_weights.get(sleeve_name, 0.0))
        target_weight = float(target_rules.get(sleeve_name, base_weight))
        vams_signal = vams_signals[symbol]
        multiplier = float(config.vams_multipliers.get(vams_signal.state, 0.0))
        actual_weight = target_weight * multiplier
        total_actual += actual_weight

        prior = prior_sleeves.get(symbol)
        delta = actual_weight - prior.actual_weight if prior is not None else None
        if prior is not None and prior.vams_state != vams_signal.state:
            signal_changes.append(
                SignalChange(
                    symbol=symbol,
                    field="vams_state",
                    old_value=prior.vams_state,
                    new_value=vams_signal.state,
                    message=f"{symbol} VAMS changed {prior.vams_state} -> {vams_signal.state}.",
                )
            )
        if prior is not None and abs(actual_weight - prior.actual_weight) > 1e-9:
            signal_changes.append(
                SignalChange(
                    symbol=symbol,
                    field="actual_weight",
                    old_value=f"{prior.actual_weight:.1%}",
                    new_value=f"{actual_weight:.1%}",
                    message=f"{symbol} actual weight moved {prior.actual_weight:.1%} -> {actual_weight:.1%}.",
                )
            )

        sleeves.append(
            SleeveAllocation(
                name=sleeve_name,
                symbol=symbol,
                base_weight=base_weight,
                target_weight=target_weight,
                actual_weight=actual_weight,
                vams_state=vams_signal.state,
                vams_multiplier=multiplier,
                regime_rule_applied=_regime_rule_name(regime.regime),
                delta_from_prior=delta,
                notes="initial snapshot" if prior is None else "",
            )
        )

    cash_symbol = config.sleeves["cash"]
    cash_weight = max(0.0, 1.0 - total_actual)
    summary_text = f"KISS is in {regime.regime.title()} with {total_actual:.0%} gross exposure and {cash_weight:.0%} in {cash_symbol}."
    implementation_text = "; ".join(
        f"Set {s.symbol} to {s.actual_weight:.0%} ({s.vams_state} vs {s.target_weight:.0%} target)"
        for s in sleeves
    ) + f"; hold residual {cash_weight:.0%} in {cash_symbol}."

    if _PRIOR_SNAPSHOT is None:
        signal_changes.insert(
            0,
            SignalChange(
                symbol="portfolio",
                field="snapshot",
                old_value="none",
                new_value="initial",
                message="Initial KISS portfolio snapshot computed.",
            )
        )
    else:
        if _PRIOR_SNAPSHOT.regime.regime != regime.regime:
            signal_changes.insert(
                0,
                SignalChange(
                    symbol="portfolio",
                    field="regime",
                    old_value=_PRIOR_SNAPSHOT.regime.regime,
                    new_value=regime.regime,
                    message=f"KISS regime changed {_PRIOR_SNAPSHOT.regime.regime} -> {regime.regime}.",
                )
            )
        prior_cash_weight = _PRIOR_SNAPSHOT.cash_weight
        if abs(cash_weight - prior_cash_weight) > 1e-9:
            signal_changes.append(
                SignalChange(
                    symbol=cash_symbol,
                    field="cash_weight",
                    old_value=f"{prior_cash_weight:.1%}",
                    new_value=f"{cash_weight:.1%}",
                    message=f"{cash_symbol} cash weight moved {prior_cash_weight:.1%} -> {cash_weight:.1%}.",
                )
            )

    snapshot = KissPortfolioSnapshot(
        regime=regime,
        sleeves=sleeves,
        cash_symbol=cash_symbol,
        cash_weight=cash_weight,
        gross_exposure=total_actual,
        summary_text=summary_text,
        implementation_text=implementation_text,
        signal_changes=signal_changes,
        as_of=regime.as_of,
    )
    _PRIOR_SNAPSHOT = snapshot
    return snapshot
