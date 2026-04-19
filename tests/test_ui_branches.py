from __future__ import annotations

from datetime import datetime

import pandas as pd
from dash import html

from app.components import ui
from app.components.layout import app_shell
from app.components.primitives import normalize_status_meta, warning_alerts
from app.models import (
    AlertFlag,
    MetricCard,
    SignalChange,
    SignalTransition,
    SleeveAllocation,
    VamsSignal,
)


def test_app_css_and_format_timestamp_branches():
    assert len(ui.APP_CSS) > 100
    assert "Unavailable" in ui._format_timestamp(None)
    ts = pd.Timestamp("2024-06-15")
    assert "2024" in ui._format_timestamp(ts)
    assert "2024" in ui._format_timestamp(datetime(2024, 6, 15))
    assert "hello" in ui._format_timestamp("hello")


def test_sparkline_pie_line_bar_exposure():
    assert ui.sparkline_chart([], semantic="positive") is not None
    assert ui.sparkline_chart([1.0, 2.0], semantic="positive") is not None
    assert ui.make_pie_chart([], [], "t") is not None
    assert ui.make_pie_chart(["A"], [1.0], "t") is not None
    df = pd.DataFrame({"report_date": [pd.Timestamp("2024-01-01")], "y": [1.0]})
    assert ui.make_line_chart(df, "report_date", ["missing"], "t") is not None
    assert ui.make_line_chart(df, "report_date", ["y"], "t", compact=True) is not None
    assert ui.make_bar_chart(pd.DataFrame({"report_date": [pd.Timestamp("2024-01-01")]}), "report_date", "t") is not None
    assert ui.make_bar_chart(pd.DataFrame({"report_date": [pd.Timestamp("2024-01-01")], "v": [1.0]}), "report_date", "t") is not None
    assert ui.make_bar_chart(pd.DataFrame({"a": [1]}), "missing_col", "t") is not None


def test_exposure_signal_meter_metric_card_sparkline():
    assert ui.exposure_gauge(None, "x") is not None
    assert ui.exposure_gauge(0.5, "x", tone="neutral") is not None
    assert ui.signal_meter(None, 0, 1, "L") is not None
    card = MetricCard("L", "v", sparkline=[0.1, 0.2, 0.3], tone="market")
    assert ui.metric_card(card) is not None


def test_delta_transition_strips_and_table():
    assert ui.delta_strip([]) is not None
    changes = [
        SignalChange("p", "cash_weight", "0%", "1%", "m"),
        SignalChange("p", "regime", "a", "b", "m"),
        SignalChange("x", "other", "a", "b", "m"),
    ]
    assert ui.delta_strip(changes) is not None
    assert ui.transition_strip([]) is not None
    assert ui.transition_strip([SignalTransition("Regime", "a", "b", None, 1, "c")]) is not None
    assert ui.transition_strip([SignalTransition("BTC-X", "a", "b", None, 1, "c")]) is not None

    df = pd.DataFrame({"a": [1], "return_1d": [0.5], "large": [2000.0]})
    assert ui.make_table(df) is not None
    assert ui.make_table(df, link_column="a", numeric_columns=["return_1d"]) is not None
    assert ui.make_table(df, column_formatters={"a": str}) is not None


def test_alerts_insight_feed():
    assert ui.alert_list([], title="A") is not None
    assert ui.alert_list([AlertFlag("S", "t", "m", "high")]) is not None
    assert ui.insight_list(["a"], "t") is not None
    assert ui.feed_panel("N", pd.DataFrame(), "t", []) is not None
    assert ui.feed_panel("N", pd.DataFrame({"title": ["x"], "z": [1]}), "title", ["z"]) is not None


def test_macro_allocation_sleeve():
    assert ui.macro_quadrant("goldilocks", 0.1, -0.1, "h") is not None
    alloc = SleeveAllocation("eq", "SPY", 0.5, 0.5, 0.5, "neutral", 0.5, "G", 0.01)
    sig = VamsSignal("SPY", "neutral", 0.0, None, None, None, None, [])
    assert ui.sleeve_state_card(alloc, sig) is not None


def test_heatstrip_semantic_map():
    assert ui.heatstrip([1.0, -1.0], ["a", "b"], semantic_map={"a": "neutral"}) is not None


def test_heatstrip_value_formats_and_none():
    assert ui.heatstrip([0.012, -0.03], ["a", "b"], value_format="percent") is not None
    assert ui.heatstrip([0.0426, 0.0055], ["a", "b"], value_format="yield") is not None
    assert ui.heatstrip([None, 0.1], ["a", "b"]) is not None


def test_benchmark_card_source_note():
    assert ui.benchmark_card("SPY", "100", "1D +1%", "positive", source_note="via Yahoo Finance") is not None


def test_normalize_status_meta_and_warning_alerts():
    meta = normalize_status_meta({})
    assert meta.get("as_of") is None and meta.get("source") == "yfinance" and meta.get("scope") == "KISS"
    assert warning_alerts([]) == []
    assert len(warning_alerts(["x"])) == 1


def test_app_shell_accepts_non_list_children():
    layout = app_shell(html.Div("solo"), page_title="t", active_page="overview", status_meta={"as_of": None})
    assert layout is not None


def test_line_chart_secondary_y_and_reference_lines():
    df = pd.DataFrame(
        {
            "report_date": pd.date_range("2024-01-01", periods=5, freq="B"),
            "a": [1.0, 1.1, 1.2, 1.3, 1.4],
            "b": [2.0, 2.1, 2.2, 2.3, 2.4],
        }
    )
    g = ui.make_line_chart(
        df,
        "report_date",
        ["a", "b"],
        "dual",
        secondary_y="b",
        y_reference=0.0,
        extra_hlines=[(1.25, "ref")],
        range_selector=True,
    )
    assert g is not None


def test_exposure_gauge_step_ranges():
    assert ui.exposure_gauge(0.4, "x", step_ranges=[(0, 50), (50, 100)]) is not None


def test_yield_curve_all_none_values():
    assert ui.yield_curve_bar(["2Y", "10Y"], [None, None], "t") is not None


def test_yield_curve_empty_inputs():
    assert ui.yield_curve_bar([], [], "t") is not None


def test_price_with_mas_branches():
    assert ui.price_with_mas(pd.DataFrame(), "SPY", {"20D": 20}, volume_column="volume") is not None
    df = pd.DataFrame(
        {
            "report_date": pd.date_range("2024-01-01", periods=260, freq="B"),
            "close": range(260),
            "volume": range(260),
        }
    )
    assert ui.price_with_mas(df, "SPY", {"20D": 20, "50D": 50, "200D": 200}, volume_column="volume", range_selector=False) is not None


def test_sparkline_semantic_else_branch():
    assert ui.sparkline_chart([1.0, 2.0], semantic="rates") is not None
