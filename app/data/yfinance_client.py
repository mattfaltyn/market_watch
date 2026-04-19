from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable

import pandas as pd

from app.data.cache import FileCache
from app.models import DataResult


@dataclass(frozen=True)
class CachePolicy:
    market_ttl_seconds: int = 900
    fundamentals_ttl_seconds: int = 21600
    news_ttl_seconds: int = 1800


# Treasury proxies: bc2_year uses ^FVX (5Y) as documented substitute for a 2Y series.
_TREASURY_TICKERS = {"bc2_year": "^FVX", "bc10_year": "^TNX", "bc30_year": "^TYX"}


def _import_yfinance():
    try:
        import yfinance as yf  # noqa: PLC0415
    except ImportError:
        return None
    return yf


def _camel_to_snake(name: str) -> str:
    s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


def _info_to_frame(info: dict[str, Any] | None) -> pd.DataFrame:
    if not info:
        return pd.DataFrame()
    row: dict[str, Any] = {}
    for key, val in info.items():
        if isinstance(val, (dict, list)):
            continue
        row[_camel_to_snake(str(key))] = val
    if not row:
        return pd.DataFrame()
    return pd.DataFrame([row])


def _history_to_price_df(symbol: str, hist: pd.DataFrame | None) -> pd.DataFrame:
    if hist is None or hist.empty:
        return pd.DataFrame()
    out = pd.DataFrame(
        {
            "symbol": symbol,
            "report_date": pd.to_datetime(hist.index, utc=True)
            .tz_convert(None)
            .normalize(),
            "open": pd.to_numeric(hist.get("Open"), errors="coerce"),
            "close": pd.to_numeric(hist.get("Close"), errors="coerce"),
            "high": pd.to_numeric(hist.get("High"), errors="coerce"),
            "low": pd.to_numeric(hist.get("Low"), errors="coerce"),
            "volume": pd.to_numeric(hist.get("Volume"), errors="coerce"),
        }
    )
    out = out.dropna(subset=["report_date", "close"])
    return out.sort_values("report_date").reset_index(drop=True)


def fetch_prices_yfinance(symbol: str) -> pd.DataFrame:
    """Load OHLCV history for ``symbol`` via yfinance; return app-shaped columns."""
    yf = _import_yfinance()
    if yf is None:
        return pd.DataFrame()
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="max", auto_adjust=False)
    except Exception:
        return pd.DataFrame()
    return _history_to_price_df(symbol, hist)


class MarketDataClient:
    """Yahoo Finance-backed market data with file caching (replaces defeatbeta-api)."""

    def __init__(
        self,
        cache: FileCache,
        policy: CachePolicy | None = None,
    ) -> None:
        self.cache = cache
        self.policy = policy or CachePolicy()
        self._price_source_by_symbol: dict[str, str] = {}

    @staticmethod
    def _normalize_frame(
        frame: pd.DataFrame | None, date_columns: tuple[str, ...] = ("report_date",)
    ) -> pd.DataFrame:
        if frame is None:
            return pd.DataFrame()
        normalized = frame.copy()
        normalized.columns = [
            str(column).strip().lower() for column in normalized.columns
        ]
        for column in date_columns:
            if column in normalized.columns:
                normalized[column] = pd.to_datetime(normalized[column], errors="coerce")
        return normalized

    def _safe_cached_frame(
        self,
        key: str,
        ttl: int,
        loader: Callable[[], pd.DataFrame],
        force_refresh: bool = False,
        date_columns: tuple[str, ...] = ("report_date",),
    ) -> DataResult:
        errors: list[str] = []

        def factory() -> pd.DataFrame:
            return self._normalize_frame(loader(), date_columns=date_columns)

        try:
            data = self.cache.get_or_set(
                key, factory, ttl_seconds=ttl, force_refresh=force_refresh
            )
        except Exception as exc:
            errors.append(str(exc))
            data = pd.DataFrame()
        return DataResult(data=data, errors=errors)

    def last_price_source(self, symbol: str) -> str | None:
        return self._price_source_by_symbol.get(symbol.upper())

    def get_prices(self, symbol: str, force_refresh: bool = False) -> DataResult:
        sym_u = symbol.upper()
        key = f"{symbol}_price__src_yfinance"

        def loader() -> pd.DataFrame:
            return fetch_prices_yfinance(symbol)

        result = self._safe_cached_frame(
            key, self.policy.market_ttl_seconds, loader, force_refresh=force_refresh
        )
        if not result.data.empty and "close" in result.data.columns:
            self._price_source_by_symbol[sym_u] = "yfinance"
        else:
            self._price_source_by_symbol.pop(sym_u, None)
        return result

    def get_return_series(
        self, symbol: str, lookbacks: list[int], force_refresh: bool = False
    ) -> DataResult:
        price_result = self.get_prices(symbol, force_refresh=force_refresh)
        if price_result.data.empty or "close" not in price_result.data.columns:
            return DataResult(data=pd.DataFrame(), errors=price_result.errors)
        frame = price_result.data.sort_values("report_date").copy()
        close = pd.to_numeric(frame["close"], errors="coerce")
        result = frame[["report_date"]].copy()
        for lookback in lookbacks:
            result[f"return_{lookback}d"] = close / close.shift(lookback) - 1.0
        return DataResult(data=result, errors=price_result.errors)

    def get_price_ratio_history(
        self, symbol_a: str, symbol_b: str, force_refresh: bool = False
    ) -> DataResult:
        left = self.get_prices(symbol_a, force_refresh=force_refresh)
        right = self.get_prices(symbol_b, force_refresh=force_refresh)
        errors = left.errors + right.errors
        if left.data.empty or right.data.empty:
            return DataResult(data=pd.DataFrame(), errors=errors)
        merged = (
            left.data[["report_date", "close"]]
            .merge(
                right.data[["report_date", "close"]],
                on="report_date",
                suffixes=("_a", "_b"),
                how="inner",
            )
            .sort_values("report_date")
        )
        if merged.empty:
            return DataResult(data=pd.DataFrame(), errors=errors)
        merged["ratio"] = pd.to_numeric(
            merged["close_a"], errors="coerce"
        ) / pd.to_numeric(merged["close_b"], errors="coerce")
        return DataResult(data=merged[["report_date", "ratio"]].dropna(), errors=errors)

    def get_yield_series(self, force_refresh: bool = False) -> DataResult:
        return self.get_treasury_yields(force_refresh=force_refresh)

    def _load_treasury_yields_frame(self) -> pd.DataFrame:
        yf = _import_yfinance()
        if yf is None:
            return pd.DataFrame()
        merged: pd.DataFrame | None = None
        for col, ysym in _TREASURY_TICKERS.items():
            try:
                hist = yf.Ticker(ysym).history(period="max", auto_adjust=False)
            except Exception:
                continue
            if hist is None or hist.empty or "Close" not in hist.columns:
                continue
            s = pd.DataFrame(
                {
                    "report_date": pd.to_datetime(hist.index, utc=True)
                    .tz_convert(None)
                    .normalize(),
                    col: pd.to_numeric(hist["Close"], errors="coerce") / 100.0,
                }
            ).dropna(subset=["report_date", col])
            if s.empty:
                continue
            merged = (
                s if merged is None else merged.merge(s, on="report_date", how="outer")
            )
        if merged is None or merged.empty:
            return pd.DataFrame()
        return merged.sort_values("report_date").reset_index(drop=True)

    def get_treasury_yields(self, force_refresh: bool = False) -> DataResult:
        return self._safe_cached_frame(
            key="treasury_yields",
            ttl=self.policy.market_ttl_seconds,
            loader=self._load_treasury_yields_frame,
            force_refresh=force_refresh,
        )

    def _load_sp500_annual_returns(self) -> pd.DataFrame:
        yf = _import_yfinance()
        if yf is None:
            return pd.DataFrame()
        try:
            hist = yf.Ticker("^GSPC").history(period="max", auto_adjust=False)
        except Exception:
            return pd.DataFrame()
        if hist is None or hist.empty or "Close" not in hist.columns:
            return pd.DataFrame()
        close = pd.to_numeric(hist["Close"], errors="coerce").dropna()
        if close.empty:
            return pd.DataFrame()
        close = close.sort_index()
        year_end = close.resample("YE").last()
        annual_returns = year_end.pct_change()
        idx = pd.DatetimeIndex(year_end.index)
        if idx.tz is not None:
            idx = idx.tz_convert(None)
        out = pd.DataFrame(
            {
                "report_date": idx.normalize(),
                "annual_returns": annual_returns.values,
            }
        ).dropna(subset=["report_date", "annual_returns"])
        return out.sort_values("report_date").reset_index(drop=True)

    def get_sp500_history(self, force_refresh: bool = False) -> DataResult:
        return self._safe_cached_frame(
            key="sp500_history",
            ttl=self.policy.fundamentals_ttl_seconds,
            loader=self._load_sp500_annual_returns,
            force_refresh=force_refresh,
        )

    def _load_info_frame(self, symbol: str) -> pd.DataFrame:
        yf = _import_yfinance()
        if yf is None:
            return pd.DataFrame()
        try:
            info = yf.Ticker(symbol).info
        except Exception:
            return pd.DataFrame()
        if not info:
            return pd.DataFrame()
        return _info_to_frame(info if isinstance(info, dict) else {})

    def get_info(self, symbol: str, force_refresh: bool = False) -> DataResult:
        return self._safe_cached_frame(
            key=f"{symbol}_info",
            ttl=self.policy.fundamentals_ttl_seconds,
            loader=lambda: self._load_info_frame(symbol),
            force_refresh=force_refresh,
            date_columns=(),
        )

    def _load_news_frame(self, symbol: str) -> pd.DataFrame:
        yf = _import_yfinance()
        if yf is None:
            return pd.DataFrame()
        try:
            raw = yf.Ticker(symbol).news
        except Exception:
            return pd.DataFrame()
        if not raw:
            return pd.DataFrame()
        rows: list[dict[str, Any]] = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            ts = item.get("providerPublishTime")
            if ts is not None:
                publish = pd.to_datetime(ts, unit="s", utc=True, errors="coerce")
            else:
                publish = pd.NaT
            rows.append(
                {
                    "publish_time": publish,
                    "title": item.get("title"),
                    "publisher": item.get("publisher", ""),
                    "source": "yfinance",
                    "report_date": publish,
                }
            )
        if not rows:
            return pd.DataFrame()
        return pd.DataFrame(rows)

    def get_news(self, symbol: str, force_refresh: bool = False) -> DataResult:
        return self._safe_cached_frame(
            key=f"{symbol}_news",
            ttl=self.policy.news_ttl_seconds,
            loader=lambda: self._load_news_frame(symbol),
            force_refresh=force_refresh,
            date_columns=("report_date", "publish_time"),
        )

    def _load_calendar_frame(self, symbol: str) -> pd.DataFrame:
        yf = _import_yfinance()
        if yf is None:
            return pd.DataFrame()
        try:
            cal = yf.Ticker(symbol).calendar
        except Exception:
            return pd.DataFrame()
        if cal is None:
            return pd.DataFrame()
        if isinstance(cal, pd.DataFrame):
            cal = cal.copy()
            cal.columns = [str(c).strip().lower() for c in cal.columns]
            if "earnings date" in cal.columns:
                cal = cal.rename(columns={"earnings date": "earning_date"})
            elif "earningdate" in cal.columns:
                cal = cal.rename(columns={"earningdate": "earning_date"})
            if "earning_date" not in cal.columns and not cal.empty:
                # first column as dates
                first = cal.iloc[:, 0]
                cal = pd.DataFrame(
                    {"earning_date": pd.to_datetime(first, errors="coerce", utc=True)}
                )
            return cal if "earning_date" in cal.columns else pd.DataFrame()
        if isinstance(cal, dict):
            dates = cal.get("Earnings Date")
            if dates is None:
                return pd.DataFrame()
            if hasattr(dates, "tolist"):
                dates = dates.tolist()
            if not isinstance(dates, list):
                dates = [dates]
            parsed = [pd.to_datetime(d, errors="coerce", utc=True) for d in dates]
            return pd.DataFrame({"earning_date": parsed})
        return pd.DataFrame()

    def get_calendar(self, symbol: str, force_refresh: bool = False) -> DataResult:
        return self._safe_cached_frame(
            key=f"{symbol}_calendar",
            ttl=self.policy.fundamentals_ttl_seconds,
            loader=lambda: self._load_calendar_frame(symbol),
            force_refresh=force_refresh,
            date_columns=("earning_date",),
        )

    def get_beta(
        self,
        symbol: str,
        benchmark: str,
        period: str = "1y",
        force_refresh: bool = False,
    ) -> DataResult:
        cache_key = f"{symbol}_beta_{benchmark}_{period}"

        def loader() -> pd.DataFrame:
            info_fr = self._load_info_frame(symbol)
            if info_fr.empty:
                return pd.DataFrame()
            row = info_fr.iloc[0]
            beta_val = None
            for key in ("beta", "beta3_year", "beta3year", "beta_3y"):
                if key in row.index and pd.notna(row.get(key)):
                    beta_val = float(row[key])
                    break
            if beta_val is None:
                return pd.DataFrame()
            today = pd.Timestamp.now(tz=timezone.utc).normalize().tz_localize(None)
            return pd.DataFrame({"report_date": [today], "beta": [beta_val]})

        return self._safe_cached_frame(
            key=cache_key,
            ttl=self.policy.market_ttl_seconds,
            loader=loader,
            force_refresh=force_refresh,
        )

    def _row_by_labels(
        self, stmt: pd.DataFrame, labels: tuple[str, ...]
    ) -> pd.Series | None:
        idx = [str(i).strip() for i in stmt.index]
        for label in labels:
            for i, name in enumerate(idx):
                if name.lower() == label.lower():
                    return stmt.iloc[i]
        for label in labels:
            for i, name in enumerate(idx):
                if label.lower() in name.lower():
                    return stmt.iloc[i]
        return None

    def _quarterly_net_margin_frame(self, symbol: str) -> pd.DataFrame:
        yf = _import_yfinance()
        if yf is None:
            return pd.DataFrame()
        try:
            stmt = yf.Ticker(symbol).quarterly_income_stmt
        except Exception:
            return pd.DataFrame()
        if stmt is None or stmt.empty:
            return pd.DataFrame()
        rev = self._row_by_labels(stmt, ("Total Revenue", "Total Revenues", "Revenue"))
        ni = self._row_by_labels(stmt, ("Net Income", "Net Income Common Stockholders"))
        if rev is None or ni is None:
            return pd.DataFrame()
        cols = [c for c in stmt.columns if pd.notna(c)]
        rows = []
        for col in cols:
            r = pd.to_numeric(rev.get(col), errors="coerce")
            n = pd.to_numeric(ni.get(col), errors="coerce")
            if pd.isna(r) or r == 0 or pd.isna(n):
                continue
            rows.append(
                {
                    "report_date": pd.to_datetime(col, errors="coerce", utc=True)
                    .tz_convert(None)
                    .normalize(),
                    "net_margin": float(n / r),
                }
            )
        return (
            pd.DataFrame(rows).sort_values("report_date").reset_index(drop=True)
            if rows
            else pd.DataFrame()
        )

    def _quarterly_yoy_frame(
        self, symbol: str, metric_labels: tuple[str, ...], out_col: str
    ) -> pd.DataFrame:
        yf = _import_yfinance()
        if yf is None:
            return pd.DataFrame()
        try:
            stmt = yf.Ticker(symbol).quarterly_income_stmt
        except Exception:
            return pd.DataFrame()
        if stmt is None or stmt.empty:
            return pd.DataFrame()
        row = self._row_by_labels(stmt, metric_labels)
        if row is None:
            return pd.DataFrame()
        cols = sorted(
            [c for c in stmt.columns if pd.notna(c)],
            key=lambda x: pd.to_datetime(x, errors="coerce"),
        )
        series = pd.Series(
            {
                pd.to_datetime(c, errors="coerce", utc=True)
                .tz_convert(None)
                .normalize(): pd.to_numeric(row.get(c), errors="coerce")
                for c in cols
            }
        )
        series = series.dropna().sort_index()
        if len(series) < 5:
            return pd.DataFrame()
        yoy = (series / series.shift(4) - 1.0).dropna()
        out = pd.DataFrame({"report_date": yoy.index, out_col: yoy.values})
        return out.dropna(subset=[out_col]).reset_index(drop=True)

    def _scalar_metric_from_info(
        self, symbol: str, column_keys: tuple[str, ...], out_column: str
    ) -> pd.DataFrame:
        info_fr = self._load_info_frame(symbol)
        if info_fr.empty:
            return pd.DataFrame()
        row = info_fr.iloc[0]
        val = None
        for ck in column_keys:
            if ck in row.index and pd.notna(row.get(ck)):
                val = float(row[ck])
                break
        if val is None:
            return pd.DataFrame()
        today = pd.Timestamp.now(tz=timezone.utc).normalize().tz_localize(None)
        return pd.DataFrame({"report_date": [today], out_column: [val]})

    def get_metric_frame(
        self,
        symbol: str,
        method_name: str,
        ttl: int | None = None,
        force_refresh: bool = False,
    ) -> DataResult:
        ttl = ttl or self.policy.fundamentals_ttl_seconds
        known = frozenset(
            {
                "ttm_pe",
                "ps_ratio",
                "pb_ratio",
                "peg_ratio",
                "roe",
                "roa",
                "roic",
                "quarterly_net_margin",
                "net_margin",
                "quarterly_revenue_yoy_growth",
                "quarterly_operating_income_yoy_growth",
                "quarterly_eps_yoy_growth",
                "industry_ttm_pe",
            }
        )
        if method_name not in known:
            return DataResult(
                data=pd.DataFrame(),
                errors=[f"{method_name} not supported for {symbol}"],
            )

        def loader() -> pd.DataFrame:
            if method_name == "ttm_pe":
                return self._scalar_metric_from_info(
                    symbol, (_camel_to_snake("trailingPE"),), "ttm_pe"
                )
            if method_name == "ps_ratio":
                return self._scalar_metric_from_info(
                    symbol,
                    (_camel_to_snake("priceToSalesTrailing12Months"),),
                    "ps_ratio",
                )
            if method_name == "pb_ratio":
                return self._scalar_metric_from_info(
                    symbol, (_camel_to_snake("priceToBook"),), "pb_ratio"
                )
            if method_name == "peg_ratio":
                return self._scalar_metric_from_info(
                    symbol, (_camel_to_snake("pegRatio"),), "peg_ratio"
                )
            if method_name == "roe":
                return self._scalar_metric_from_info(
                    symbol, (_camel_to_snake("returnOnEquity"),), "roe"
                )
            if method_name == "roa":
                return self._scalar_metric_from_info(
                    symbol, (_camel_to_snake("returnOnAssets"),), "roa"
                )
            if method_name == "roic":
                return self._scalar_metric_from_info(
                    symbol, (_camel_to_snake("returnOnAssets"),), "roic"
                )
            if method_name in ("quarterly_net_margin", "net_margin"):
                return self._quarterly_net_margin_frame(symbol)
            if method_name == "quarterly_revenue_yoy_growth":
                return self._quarterly_yoy_frame(
                    symbol,
                    ("Total Revenue", "Total Revenues", "Revenue"),
                    "revenue_yoy_growth",
                )
            if method_name == "quarterly_operating_income_yoy_growth":
                return self._quarterly_yoy_frame(
                    symbol,
                    ("Operating Income", "Total Operating Income"),
                    "operating_income_yoy_growth",
                )
            if method_name == "quarterly_eps_yoy_growth":
                return self._quarterly_yoy_frame(
                    symbol, ("Basic EPS", "Diluted EPS"), "eps_yoy_growth"
                )
            return pd.DataFrame()

        return self._safe_cached_frame(
            key=f"{symbol}_{method_name}",
            ttl=ttl,
            loader=loader,
            force_refresh=force_refresh,
            date_columns=(
                "report_date",
                "eps_report_date",
                "shares_report_date",
                "exchange_report_date",
                "fiscal_quarter",
            ),
        )

    @staticmethod
    def latest_timestamp(frames: list[pd.DataFrame]) -> datetime | None:
        timestamps: list[pd.Timestamp] = []
        for frame in frames:
            if "report_date" in frame.columns and not frame.empty:
                timestamps.append(frame["report_date"].dropna().max())
        if not timestamps:
            return None
        return max(timestamps).to_pydatetime()


class YFinanceFetcher:
    """Callable wrapper for tests and legacy call sites."""

    def fetch_prices(self, symbol: str) -> pd.DataFrame:
        return fetch_prices_yfinance(symbol)
