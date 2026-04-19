from __future__ import annotations

import pandas as pd

from app.models import TickerDetailBundle
from app.services.market_snapshot import build_rates_snapshot
from app.services.signals import get_alert_flags


def _utc_midnight() -> pd.Timestamp:
    return pd.Timestamp.now(tz="UTC").normalize()


def _coerce_utc(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, errors="coerce", utc=True)


def _latest_close_and_trend(price_frame: pd.DataFrame) -> dict[str, object]:
    if price_frame.empty or "close" not in price_frame.columns:
        return {
            "close": None,
            "return_1d": None,
            "return_5d": None,
            "return_1m": None,
            "ma50_state": "unavailable",
            "ma200_state": "unavailable",
        }
    frame = price_frame.sort_values("report_date").copy()
    close = pd.to_numeric(frame["close"], errors="coerce")
    latest = close.iloc[-1]
    return {
        "close": float(latest),
        "return_1d": float(close.iloc[-1] / close.iloc[-2] - 1.0) if len(close) > 1 else None,
        "return_5d": float(close.iloc[-1] / close.iloc[-6] - 1.0) if len(close) > 5 else None,
        "return_1m": float(close.iloc[-1] / close.iloc[-22] - 1.0) if len(close) > 21 else None,
        "ma50_state": "above" if len(close) >= 50 and latest >= close.rolling(50).mean().iloc[-1] else "below" if len(close) >= 50 else "unavailable",
        "ma200_state": "above" if len(close) >= 200 and latest >= close.rolling(200).mean().iloc[-1] else "below" if len(close) >= 200 else "unavailable",
    }


def _latest_value(frame: pd.DataFrame, column: str) -> float | None:
    if frame.empty or column not in frame.columns:
        return None
    series = pd.to_numeric(frame[column], errors="coerce").dropna()
    if series.empty:
        return None
    return float(series.iloc[-1])


def _next_earnings_days(calendar_frame: pd.DataFrame) -> float | None:
    if calendar_frame.empty or "earning_date" not in calendar_frame.columns:
        return None
    earning_dates = _coerce_utc(calendar_frame["earning_date"]).dropna()
    if earning_dates.empty:
        return None
    today = _utc_midnight()
    future_dates = earning_dates[earning_dates >= today]
    if future_dates.empty:
        return None
    return float((future_dates.min() - today).days)


def build_watchlist_snapshot(client, tickers: list[str], benchmark: str, thresholds: dict[str, float], force_refresh: bool = False) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    rates = build_rates_snapshot(client, force_refresh=force_refresh)

    for symbol in tickers:
        price = client.get_prices(symbol, force_refresh=force_refresh)
        beta = client.get_beta(symbol, benchmark=benchmark, force_refresh=force_refresh)
        calendar = client.get_calendar(symbol, force_refresh=force_refresh)
        news = client.get_news(symbol, force_refresh=force_refresh)
        ttm_pe = client.get_metric_frame(symbol, "ttm_pe", force_refresh=force_refresh)
        industry_pe = client.get_metric_frame(symbol, "industry_ttm_pe", force_refresh=force_refresh)
        net_margin = client.get_metric_frame(symbol, "quarterly_net_margin", force_refresh=force_refresh)
        revenue_growth = client.get_metric_frame(symbol, "quarterly_revenue_yoy_growth", force_refresh=force_refresh)

        trend = _latest_close_and_trend(price.data)
        pe_value = _latest_value(ttm_pe.data, "ttm_pe")
        industry_pe_value = _latest_value(industry_pe.data, "industry_ttm_pe")
        publish_col = "publish_time" if "publish_time" in news.data.columns else "report_date"
        now_utc = _utc_midnight()
        recent_news_3d = int((_coerce_utc(news.data[publish_col]) >= now_utc - pd.Timedelta(days=3)).sum()) if not news.data.empty and publish_col in news.data.columns else 0
        recent_news_7d = int((_coerce_utc(news.data[publish_col]) >= now_utc - pd.Timedelta(days=7)).sum()) if not news.data.empty and publish_col in news.data.columns else 0

        row = {
            "symbol": symbol,
            **trend,
            "beta_1y": _latest_value(beta.data, "beta"),
            "days_to_earnings": _next_earnings_days(calendar.data),
            "ttm_pe": pe_value,
            "industry_ttm_pe": industry_pe_value,
            "ttm_pe_vs_industry": ((pe_value / industry_pe_value) - 1.0) if pe_value and industry_pe_value else None,
            "net_margin": _latest_value(net_margin.data, "net_margin"),
            "revenue_yoy_growth": _latest_value(revenue_growth.data, "revenue_yoy_growth"),
            "recent_news_3d": recent_news_3d,
            "recent_news_7d": recent_news_7d,
            "errors": " | ".join(price.errors + beta.errors + calendar.errors + news.errors),
        }
        flags = get_alert_flags(symbol, pd.Series(row), rates, thresholds)
        row["alerts"] = [flag.message for flag in flags]
        row["alert_count"] = len(flags)
        row["high_alert_count"] = sum(1 for flag in flags if flag.severity == "high")
        row["medium_alert_count"] = sum(1 for flag in flags if flag.severity == "medium")
        rows.append(row)

    return pd.DataFrame(rows)


def get_ticker_detail(client, symbol: str, alerts, force_refresh: bool = False, role_label: str | None = None) -> TickerDetailBundle:
    info = client.get_info(symbol, force_refresh=force_refresh)
    price = client.get_prices(symbol, force_refresh=force_refresh)
    news = client.get_news(symbol, force_refresh=force_refresh)
    calendar = client.get_calendar(symbol, force_refresh=force_refresh)
    valuation = {
        "ttm_pe": client.get_metric_frame(symbol, "ttm_pe", force_refresh=force_refresh).data,
        "ps_ratio": client.get_metric_frame(symbol, "ps_ratio", force_refresh=force_refresh).data,
        "pb_ratio": client.get_metric_frame(symbol, "pb_ratio", force_refresh=force_refresh).data,
        "peg_ratio": client.get_metric_frame(symbol, "peg_ratio", force_refresh=force_refresh).data,
    }
    quality = {
        "roe": client.get_metric_frame(symbol, "roe", force_refresh=force_refresh).data,
        "roa": client.get_metric_frame(symbol, "roa", force_refresh=force_refresh).data,
        "roic": client.get_metric_frame(symbol, "roic", force_refresh=force_refresh).data,
        "net_margin": client.get_metric_frame(symbol, "quarterly_net_margin", force_refresh=force_refresh).data,
    }
    growth = {
        "revenue_yoy_growth": client.get_metric_frame(symbol, "quarterly_revenue_yoy_growth", force_refresh=force_refresh).data,
        "operating_income_yoy_growth": client.get_metric_frame(symbol, "quarterly_operating_income_yoy_growth", force_refresh=force_refresh).data,
        "eps_yoy_growth": client.get_metric_frame(symbol, "quarterly_eps_yoy_growth", force_refresh=force_refresh).data,
    }
    errors = info.errors + price.errors + news.errors + calendar.errors
    as_of = None
    if not price.data.empty and "report_date" in price.data.columns:
        ts = price.data["report_date"].max()
        if ts is not None and not pd.isna(ts):
            as_of = pd.Timestamp(ts).to_pydatetime()
    return TickerDetailBundle(
        symbol=symbol,
        info=info.data,
        price=price.data,
        valuation=valuation,
        quality=quality,
        growth=growth,
        news=news.data,
        calendar=calendar.data,
        alerts=alerts,
        errors=errors,
        role_label=role_label,
        as_of=as_of,
    )
