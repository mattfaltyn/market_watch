import pandas as pd

from app.models import MarketIndexSnapshot, MarketSnapshot, RatesSnapshot
from app.services.signals import compute_regime


def _snapshot(symbol: str, ma50: str, ma200: str, return_1m: float) -> MarketIndexSnapshot:
    return MarketIndexSnapshot(symbol, 100.0, 0.01, 0.02, return_1m, 0.15, "above", ma50, ma200, None)


def test_compute_regime_risk_on():
    market = MarketSnapshot(
        indices=[
            _snapshot("SPY", "above", "above", 0.05),
            _snapshot("QQQ", "above", "above", 0.06),
            _snapshot("IWM", "above", "above", 0.03),
        ],
        positive_participation_ratio=1.0,
        as_of=None,
    )
    rates = RatesSnapshot(None, 0.04, 0.04, 0.045, 0.002, -0.001, -0.003)
    watchlist = pd.DataFrame({"return_1m": [0.04, 0.02, 0.01]})
    regime = compute_regime(market, rates, watchlist)
    assert regime.regime == "Risk-On"


def test_compute_regime_risk_off():
    market = MarketSnapshot(
        indices=[
            _snapshot("SPY", "below", "below", -0.05),
            _snapshot("QQQ", "below", "below", -0.04),
            _snapshot("IWM", "below", "below", -0.02),
        ],
        positive_participation_ratio=0.0,
        as_of=None,
    )
    rates = RatesSnapshot(None, 0.05, 0.04, 0.045, -0.01, 0.002, 0.003)
    watchlist = pd.DataFrame({"return_1m": [-0.04, -0.02, 0.01]})
    regime = compute_regime(market, rates, watchlist)
    assert regime.regime == "Risk-Off"
