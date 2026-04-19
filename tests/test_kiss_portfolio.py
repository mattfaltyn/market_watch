import app.services.kiss_portfolio as kiss_portfolio
from app.models import KissRegime, VamsSignal
from app.services.kiss_portfolio import build_kiss_portfolio_snapshot


class FakeConfig:
    sleeves = {"equity": "SPY", "fixed_income": "AGG", "bitcoin": "BTC-USD", "cash": "USFR"}
    base_weights = {"equity": 0.6, "fixed_income": 0.3, "bitcoin": 0.1}
    regime_rules = {
        "goldilocks": {"equity": 0.6, "fixed_income": 0.3, "bitcoin": 0.1},
        "inflation": {"equity": 0.3, "fixed_income": 0.15, "bitcoin": 0.05},
    }
    vams_multipliers = {"bullish": 1.0, "neutral": 0.5, "bearish": 0.0}


def setup_function():
    kiss_portfolio._PRIOR_SNAPSHOT = None


def test_build_kiss_portfolio_snapshot_uses_targets_and_vams():
    regime = KissRegime("goldilocks", 0.4, None, "up", "down", {}, None, ["Growth up"])
    vams = {
        "SPY": VamsSignal("SPY", "neutral", 0.0, 0.1, 0.1, 0.1, None),
        "AGG": VamsSignal("AGG", "bullish", 0.0, 0.1, 0.1, 0.1, None),
        "BTC-USD": VamsSignal("BTC-USD", "neutral", 0.0, 0.1, 0.1, 0.1, None),
    }
    snapshot = build_kiss_portfolio_snapshot(regime, vams, FakeConfig())
    actuals = {s.symbol: s.actual_weight for s in snapshot.sleeves}
    assert actuals["SPY"] == 0.30
    assert actuals["AGG"] == 0.30
    assert actuals["BTC-USD"] == 0.05
    assert snapshot.cash_weight == 0.35


def test_build_kiss_portfolio_snapshot_does_not_reuse_stale_change_log():
    regime = KissRegime("goldilocks", 0.4, None, "up", "down", {}, None, ["Growth up"])
    vams = {
        "SPY": VamsSignal("SPY", "neutral", 0.0, 0.1, 0.1, 0.1, None),
        "AGG": VamsSignal("AGG", "bullish", 0.0, 0.1, 0.1, 0.1, None),
        "BTC-USD": VamsSignal("BTC-USD", "neutral", 0.0, 0.1, 0.1, 0.1, None),
    }
    first = build_kiss_portfolio_snapshot(regime, vams, FakeConfig())
    second = build_kiss_portfolio_snapshot(regime, vams, FakeConfig())

    assert first.signal_changes
    assert second.signal_changes == []
