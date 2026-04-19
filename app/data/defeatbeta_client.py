from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Callable

import pandas as pd

from app.data.cache import FileCache
from app.models import DataResult


@dataclass(frozen=True)
class CachePolicy:
    market_ttl_seconds: int = 900
    fundamentals_ttl_seconds: int = 21600
    news_ttl_seconds: int = 1800
    filings_ttl_seconds: int = 21600
    transcripts_ttl_seconds: int = 43200


class DefeatBetaClient:
    def __init__(
        self,
        cache: FileCache,
        policy: CachePolicy | None = None,
        price_fetch_overrides: dict[str, str] | None = None,
        fallback_fetcher: Callable[[str], pd.DataFrame] | None = None,
    ) -> None:
        self.cache = cache
        self.policy = policy or CachePolicy()
        self._price_fetch_overrides = price_fetch_overrides or {}
        self._fallback_fetcher = fallback_fetcher
        self._price_source_by_symbol: dict[str, str] = {}
        self._ticker_cls = None
        self._treasure_cls = None
        self._util_module = None

    def _resolve_price_fetch_symbol(self, symbol: str) -> str:
        o = self._price_fetch_overrides
        if symbol in o:
            return o[symbol]
        upper = symbol.upper()
        if upper in o:
            return o[upper]
        return symbol

    def _lazy_import(self) -> None:
        if self._ticker_cls is not None:
            return
        try:
            from defeatbeta_api.data.ticker import Ticker
            from defeatbeta_api.data.treasure import Treasure
            from defeatbeta_api.utils import util
        except ImportError as exc:
            raise RuntimeError(
                "defeatbeta-api is required to run the dashboard. Install project dependencies first."
            ) from exc
        self._ticker_cls = Ticker
        self._treasure_cls = Treasure
        self._util_module = util

    @staticmethod
    def _normalize_frame(frame: pd.DataFrame, date_columns: tuple[str, ...] = ("report_date",)) -> pd.DataFrame:
        if frame is None:
            return pd.DataFrame()
        normalized = frame.copy()
        normalized.columns = [str(column).strip().lower() for column in normalized.columns]
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
            data = self.cache.get_or_set(key, factory, ttl_seconds=ttl, force_refresh=force_refresh)
        except Exception as exc:
            errors.append(str(exc))
            data = pd.DataFrame()
        return DataResult(data=data, errors=errors)

    def _ticker(self, symbol: str):
        self._lazy_import()
        return self._ticker_cls(symbol)

    def _defeatbeta_price_cache_key(self, symbol: str, fetch_symbol: str) -> str:
        sym_u = symbol.upper()
        fs_u = fetch_symbol.upper()
        if fs_u == sym_u:
            return f"{symbol}_price__src_defeatbeta"
        return f"{symbol}_price__via_{fetch_symbol}__src_defeatbeta"

    def last_price_source(self, symbol: str) -> str | None:
        """``defeatbeta`` or ``yfinance`` for the last successful ``get_prices`` for this logical symbol."""
        return self._price_source_by_symbol.get(symbol.upper())

    def get_prices(self, symbol: str, force_refresh: bool = False) -> DataResult:
        fetch_symbol = self._resolve_price_fetch_symbol(symbol)
        sym_u = symbol.upper()
        primary_key = self._defeatbeta_price_cache_key(symbol, fetch_symbol)
        ticker = self._ticker(fetch_symbol)
        primary = self._safe_cached_frame(
            key=primary_key,
            ttl=self.policy.market_ttl_seconds,
            loader=ticker.price,
            force_refresh=force_refresh,
        )
        errors = list(primary.errors)
        data = primary.data
        if not data.empty and "close" in data.columns:
            self._price_source_by_symbol[sym_u] = "defeatbeta"
            return DataResult(data=data, errors=errors)

        if self._fallback_fetcher is None:
            self._price_source_by_symbol.pop(sym_u, None)
            return DataResult(data=pd.DataFrame(), errors=errors)

        def yf_loader() -> pd.DataFrame:
            return self._normalize_frame(self._fallback_fetcher(symbol))

        fb_key = f"{symbol}_price__src_yfinance"
        fallback = self._safe_cached_frame(
            key=fb_key,
            ttl=self.policy.market_ttl_seconds,
            loader=yf_loader,
            force_refresh=force_refresh,
        )
        errors.extend(fallback.errors)
        if not fallback.data.empty and "close" in fallback.data.columns:
            self._price_source_by_symbol[sym_u] = "yfinance"
            return DataResult(data=fallback.data, errors=errors)

        self._price_source_by_symbol.pop(sym_u, None)
        return DataResult(data=pd.DataFrame(), errors=errors)

    def get_return_series(self, symbol: str, lookbacks: list[int], force_refresh: bool = False) -> DataResult:
        price_result = self.get_prices(symbol, force_refresh=force_refresh)
        if price_result.data.empty or "close" not in price_result.data.columns:
            return DataResult(data=pd.DataFrame(), errors=price_result.errors)
        frame = price_result.data.sort_values("report_date").copy()
        close = pd.to_numeric(frame["close"], errors="coerce")
        result = frame[["report_date"]].copy()
        for lookback in lookbacks:
            result[f"return_{lookback}d"] = close / close.shift(lookback) - 1.0
        return DataResult(data=result, errors=price_result.errors)

    def get_price_ratio_history(self, symbol_a: str, symbol_b: str, force_refresh: bool = False) -> DataResult:
        left = self.get_prices(symbol_a, force_refresh=force_refresh)
        right = self.get_prices(symbol_b, force_refresh=force_refresh)
        errors = left.errors + right.errors
        if left.data.empty or right.data.empty:
            return DataResult(data=pd.DataFrame(), errors=errors)
        merged = left.data[["report_date", "close"]].merge(
            right.data[["report_date", "close"]],
            on="report_date",
            suffixes=("_a", "_b"),
            how="inner",
        ).sort_values("report_date")
        if merged.empty:
            return DataResult(data=pd.DataFrame(), errors=errors)
        merged["ratio"] = pd.to_numeric(merged["close_a"], errors="coerce") / pd.to_numeric(merged["close_b"], errors="coerce")
        return DataResult(data=merged[["report_date", "ratio"]].dropna(), errors=errors)

    def get_yield_series(self, force_refresh: bool = False) -> DataResult:
        return self.get_treasury_yields(force_refresh=force_refresh)

    def get_beta(self, symbol: str, benchmark: str, period: str = "1y", force_refresh: bool = False) -> DataResult:
        ticker = self._ticker(symbol)
        return self._safe_cached_frame(
            key=f"{symbol}_beta_{benchmark}_{period}",
            ttl=self.policy.market_ttl_seconds,
            loader=lambda: ticker.beta(period=period, benchmark=benchmark),
            force_refresh=force_refresh,
        )

    def get_calendar(self, symbol: str, force_refresh: bool = False) -> DataResult:
        ticker = self._ticker(symbol)
        return self._safe_cached_frame(
            key=f"{symbol}_calendar",
            ttl=self.policy.fundamentals_ttl_seconds,
            loader=ticker.calendar,
            force_refresh=force_refresh,
        )

    def get_info(self, symbol: str, force_refresh: bool = False) -> DataResult:
        ticker = self._ticker(symbol)
        return self._safe_cached_frame(
            key=f"{symbol}_info",
            ttl=self.policy.fundamentals_ttl_seconds,
            loader=ticker.info,
            force_refresh=force_refresh,
        )

    def get_news(self, symbol: str, force_refresh: bool = False) -> DataResult:
        ticker = self._ticker(symbol)
        return self._safe_cached_frame(
            key=f"{symbol}_news",
            ttl=self.policy.news_ttl_seconds,
            loader=lambda: ticker.news().get_all_news(),
            force_refresh=force_refresh,
            date_columns=("report_date", "publish_time"),
        )

    def get_filings(self, symbol: str, force_refresh: bool = False) -> DataResult:
        ticker = self._ticker(symbol)
        return self._safe_cached_frame(
            key=f"{symbol}_filings",
            ttl=self.policy.filings_ttl_seconds,
            loader=ticker.sec_filing,
            force_refresh=force_refresh,
            date_columns=("report_date", "filing_date", "acceptance_date_time"),
        )

    def get_transcripts(self, symbol: str, force_refresh: bool = False) -> DataResult:
        ticker = self._ticker(symbol)
        return self._safe_cached_frame(
            key=f"{symbol}_transcripts",
            ttl=self.policy.transcripts_ttl_seconds,
            loader=lambda: ticker.earning_call_transcripts().get_transcripts_list(),
            force_refresh=force_refresh,
            date_columns=("report_date", "earnings_date"),
        )

    def get_revenue_by_segment(self, symbol: str, force_refresh: bool = False) -> DataResult:
        ticker = self._ticker(symbol)
        return self._safe_cached_frame(
            key=f"{symbol}_revenue_segment",
            ttl=self.policy.fundamentals_ttl_seconds,
            loader=ticker.revenue_by_segment,
            force_refresh=force_refresh,
        )

    def get_revenue_by_geography(self, symbol: str, force_refresh: bool = False) -> DataResult:
        ticker = self._ticker(symbol)
        return self._safe_cached_frame(
            key=f"{symbol}_revenue_geo",
            ttl=self.policy.fundamentals_ttl_seconds,
            loader=ticker.revenue_by_geography,
            force_refresh=force_refresh,
        )

    def get_treasury_yields(self, force_refresh: bool = False) -> DataResult:
        self._lazy_import()
        treasure = self._treasure_cls()
        return self._safe_cached_frame(
            key="treasury_yields",
            ttl=self.policy.market_ttl_seconds,
            loader=treasure.daily_treasure_yield,
            force_refresh=force_refresh,
        )

    def get_sp500_history(self, force_refresh: bool = False) -> DataResult:
        self._lazy_import()
        return self._safe_cached_frame(
            key="sp500_history",
            ttl=self.policy.fundamentals_ttl_seconds,
            loader=self._util_module.load_sp500_historical_annual_returns,
            force_refresh=force_refresh,
        )

    def get_sp500_cagr(self, years: int, force_refresh: bool = False) -> DataResult:
        self._lazy_import()
        return self._safe_cached_frame(
            key=f"sp500_cagr_{years}",
            ttl=self.policy.fundamentals_ttl_seconds,
            loader=lambda: self._util_module.sp500_cagr_returns(years),
            force_refresh=force_refresh,
        )

    def get_sp500_cagr_rolling(self, years: int, force_refresh: bool = False) -> DataResult:
        self._lazy_import()
        return self._safe_cached_frame(
            key=f"sp500_cagr_rolling_{years}",
            ttl=self.policy.fundamentals_ttl_seconds,
            loader=lambda: self._util_module.sp500_cagr_returns_rolling(years),
            force_refresh=force_refresh,
            date_columns=("start_date", "end_date"),
        )

    def get_metric_frame(self, symbol: str, method_name: str, ttl: int | None = None, force_refresh: bool = False) -> DataResult:
        ticker = self._ticker(symbol)
        if not hasattr(ticker, method_name):
            return DataResult(data=pd.DataFrame(), errors=[f"{method_name} not supported for {symbol}"])
        loader = getattr(ticker, method_name)
        return self._safe_cached_frame(
            key=f"{symbol}_{method_name}",
            ttl=ttl or self.policy.fundamentals_ttl_seconds,
            loader=loader,
            force_refresh=force_refresh,
            date_columns=("report_date", "eps_report_date", "shares_report_date", "exchange_report_date", "fiscal_quarter"),
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
