from __future__ import annotations

import pandas as pd


def fetch_prices_yfinance(symbol: str) -> pd.DataFrame:
    """Load OHLCV history for ``symbol`` via yfinance; return defeatbeta-shaped columns.

    Returns an empty DataFrame on import failure or fetch errors.
    """
    try:
        import yfinance as yf
    except ImportError:
        return pd.DataFrame()

    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="max", auto_adjust=False)
    except Exception:
        return pd.DataFrame()

    if hist is None or hist.empty:
        return pd.DataFrame()

    out = pd.DataFrame(
        {
            "symbol": symbol,
            "report_date": pd.to_datetime(hist.index, utc=True).tz_convert(None).normalize(),
            "open": pd.to_numeric(hist.get("Open"), errors="coerce"),
            "close": pd.to_numeric(hist.get("Close"), errors="coerce"),
            "high": pd.to_numeric(hist.get("High"), errors="coerce"),
            "low": pd.to_numeric(hist.get("Low"), errors="coerce"),
            "volume": pd.to_numeric(hist.get("Volume"), errors="coerce"),
        }
    )
    out = out.dropna(subset=["report_date", "close"])
    return out.sort_values("report_date").reset_index(drop=True)


class YFinanceFetcher:
    """Callable wrapper for dependency injection into ``DefeatBetaClient``."""

    def fetch_prices(self, symbol: str) -> pd.DataFrame:
        return fetch_prices_yfinance(symbol)
