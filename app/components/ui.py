"""Backward-compatible exports for Dash pages. Prefer importing from submodules."""

from __future__ import annotations

from app.components.charts import (
    exposure_gauge,
    make_bar_chart,
    make_line_chart,
    make_pie_chart,
    price_with_mas,
    sparkline_chart,
    yield_curve_bar,
)
from app.components.layout import app_shell, fatal_error_page
from app.components.primitives import (
    allocation_band,
    alert_list,
    badge,
    benchmark_card,
    delta_strip,
    error_box,
    feed_panel,
    format_timestamp,
    heatstrip,
    insight_list,
    macro_quadrant,
    metric_card,
    section_panel,
    signal_meter,
    sleeve_state_card,
    stat_chip,
    transition_strip,
    warning_alerts,
)
from app.components.tables import _format_numeric, make_table
from app.components.theme import COLOR_MAP, SERIES_PALETTE, SLEEVE_COLORS, THEME, plotly_template, series_color

__all__ = [
    "COLOR_MAP",
    "SERIES_PALETTE",
    "SLEEVE_COLORS",
    "THEME",
    "APP_CSS",
    "allocation_band",
    "alert_list",
    "app_shell",
    "badge",
    "benchmark_card",
    "delta_strip",
    "error_box",
    "exposure_gauge",
    "fatal_error_page",
    "feed_panel",
    "heatstrip",
    "insight_list",
    "macro_quadrant",
    "make_bar_chart",
    "make_line_chart",
    "make_pie_chart",
    "make_table",
    "metric_card",
    "plotly_template",
    "price_with_mas",
    "section_panel",
    "series_color",
    "signal_meter",
    "sleeve_state_card",
    "sparkline_chart",
    "stat_chip",
    "transition_strip",
    "warning_alerts",
    "yield_curve_bar",
    "format_timestamp",
    "_format_numeric",
]

# Tests and legacy callers
_format_timestamp = format_timestamp

# Mantine handles most typography; keep layout/grid/quadrant/terminal styles
APP_CSS = """
:root {
  --bg: #07111a;
  --text: #e6f1ff;
  --text-muted: #91a7bd;
  --border: rgba(127, 150, 173, 0.18);
  --shadow: 0 24px 48px rgba(0, 0, 0, 0.38);
}
* { box-sizing: border-box; }
body {
  margin: 0;
  font-family: "IBM Plex Sans", "Inter", sans-serif;
  background: linear-gradient(180deg, var(--bg) 0%, #050d14 100%);
  color: var(--text);
}
a { color: #d5e7f7; text-decoration: none; font-weight: 600; }
.app-shell { min-height: 100vh; }
.app-frame { margin: 0 auto; max-width: 1480px; }
.page-body-wrap { padding: 24px 22px 52px; }
.page-body { max-width: 1480px; margin: 0 auto; display: grid; gap: 18px; }
.hero-grid, .two-col, .info-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 18px; }
.three-col { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 18px; }
.four-col { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 14px; }
.kpi-strip { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 14px; }
.sleeve-grid, .signal-grid, .proxy-grid, .chart-wall { display: grid; grid-template-columns: repeat(auto-fit, minmax(230px, 1fr)); gap: 16px; }
.section.panel .section-body { margin-top: 8px; }
.metric-card { min-height: 120px; }
.refresh-button {
  border: 1px solid rgba(91, 192, 255, 0.25); border-radius: 999px;
  background: linear-gradient(135deg, #0f2738 0%, #173a56 100%);
  color: white; padding: 12px 18px; font-weight: 700; cursor: pointer;
}
.macro-quadrant { position: relative; min-height: 320px; }
.quadrant-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; }
.quadrant-cell {
  min-height: 128px; padding: 16px; border-radius: 18px; border: 1px solid rgba(127,150,173,0.16);
  background: rgba(18, 34, 49, 0.72); display: grid; align-content: end; gap: 8px;
}
.quadrant-cell.is-active { border-color: rgba(91,192,255,0.62); box-shadow: inset 0 0 0 1px rgba(91,192,255,0.34); }
.quadrant-cell-label { font-size: 16px; font-weight: 700; letter-spacing: 0.06em; }
.quadrant-cell-text { color: var(--text-muted); font-size: 12px; }
.quadrant-label { position: absolute; font-size: 10px; letter-spacing: 0.12em; text-transform: uppercase; color: #667b91; }
.x-axis-pos { right: 18px; bottom: -4px; }
.x-axis-neg { left: 18px; bottom: -4px; }
.y-axis-pos { top: -6px; right: 22px; }
.y-axis-neg { bottom: 30px; left: -2px; transform: rotate(-90deg); transform-origin: left bottom; }
.quadrant-point {
  position: absolute; width: 16px; height: 16px; border-radius: 999px; background: #ff9f43; border: 2px solid #07111a;
  box-shadow: 0 0 0 4px rgba(255,159,67,0.22);
  z-index: 2;
}
@keyframes quadrant-pulse {
  0%, 100% { box-shadow: 0 0 0 4px rgba(255,159,67,0.22); }
  50% { box-shadow: 0 0 0 8px rgba(255,159,67,0.35); }
}
.quadrant-point-pulse { animation: quadrant-pulse 2.5s ease-in-out infinite; }
.quadrant-summary { margin-top: 16px; display: flex; gap: 8px; flex-wrap: wrap; }
.signal-meter { display: grid; gap: 6px; }
.signal-meter-head { display: flex; justify-content: space-between; color: var(--text-muted); font-size: 11px; }
.signal-meter-track { position: relative; height: 8px; border-radius: 999px; background: rgba(127,150,173,0.12); overflow: visible; }
.signal-meter-thumb { position: absolute; top: 0; width: 16px; height: 8px; border-radius: 999px; transform: translateX(-50%); }
.signal-meter-thumb.tone-market { background: #5bc0ff; }
.signal-meter-thumb.tone-rates, .signal-meter-thumb.tone-warning { background: #ffb347; }
.signal-meter-thumb.tone-positive, .signal-meter-thumb.tone-bullish { background: #33d17a; }
.signal-meter-thumb.tone-negative, .signal-meter-thumb.tone-bearish { background: #ff6b6b; }
.signal-meter-thumb.tone-neutral_state { background: #8aa4bf; }
.stat-chip {
  display: grid; gap: 4px; padding: 10px 12px; border-radius: 12px;
  background: rgba(18, 34, 49, 0.8); border: 1px solid rgba(127, 150, 173, 0.14);
}
.stat-chip-label { font-size: 10px; letter-spacing: 0.10em; text-transform: uppercase; color: #667b91; }
.stat-chip-value { font-size: 12px; color: var(--text); }
.tone-positive, .tone-bullish { border-color: rgba(51,209,122,0.35); }
.tone-negative, .tone-bearish { border-color: rgba(255,107,107,0.35); }
.tone-warning, .tone-rates { border-color: rgba(255,179,71,0.35); }
.tone-market { border-color: rgba(91,192,255,0.35); }
.tone-neutral_state { border-color: rgba(138,164,191,0.28); }
.benchmark-tile { min-height: 100px; }
.delta-strip { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; }
.delta-event {
  padding: 12px; border-radius: 16px; background: rgba(18,34,49,0.82); border: 1px solid rgba(127,150,173,0.16); display: grid; gap: 6px;
}
.delta-symbol { font-size: 11px; letter-spacing: 0.12em; text-transform: uppercase; color: #667b91; }
.delta-field { font-size: 14px; font-weight: 700; }
.delta-transition { font-size: 12px; color: var(--text-muted); }
.delta-strip.empty { padding: 14px; border-radius: 16px; background: rgba(18,34,49,0.72); border: 1px dashed rgba(127,150,173,0.16); }
.heatstrip { display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 10px; }
.heat-cell {
  padding: 10px 12px; border-radius: 14px; background: rgba(18,34,49,0.82); border: 1px solid rgba(127,150,173,0.14); display: grid; gap: 6px;
}
.heat-label { font-size: 10px; text-transform: uppercase; letter-spacing: 0.10em; color: #667b91; }
.heat-value { font-size: 16px; font-weight: 700; }
.empty-state {
  padding: 16px; border-radius: 14px; background: rgba(18,34,49,0.72); border: 1px dashed rgba(127,150,173,0.16); color: var(--text-muted); font-size: 12px;
}
.warning-rack { display: grid; gap: 8px; }
.warning-title { font-size: 11px; letter-spacing: 0.12em; text-transform: uppercase; color: #ffb347; }
.warning-item { background: rgba(18,34,49,0.82); border: 1px solid rgba(255,179,71,0.16); border-radius: 12px; padding: 10px 12px; color: #ffd8a8; }
.guidance-item { background: rgba(18,34,49,0.82); border: 1px solid rgba(91,192,255,0.16); border-radius: 12px; padding: 10px 12px; color: #d5e7f7; font-size: 12px; }
.sparkline .js-plotly-plot, .chart .js-plotly-plot { width: 100% !important; }
.sleeve-card { padding: 16px; display: grid; gap: 12px; border-radius: 16px; border: 1px solid var(--border); background: rgba(15,27,40,0.96); }
.allocation-band { display: grid; gap: 14px; }
.allocation-legend { display: flex; gap: 12px; flex-wrap: wrap; }
.legend-item { display: flex; align-items: center; gap: 8px; color: var(--text-muted); font-size: 12px; }
.allocation-rows { display: grid; gap: 12px; }
.allocation-row { display: grid; grid-template-columns: 80px 1fr minmax(180px, 260px); gap: 12px; align-items: center; }
.allocation-row-label { font-size: 11px; letter-spacing: 0.12em; text-transform: uppercase; color: #667b91; }
.allocation-track { display: flex; height: 18px; border-radius: 999px; overflow: hidden; background: rgba(127,150,173,0.10); border: 1px solid rgba(127,150,173,0.12); }
.allocation-segment { height: 100%; }
.allocation-row-values { font-size: 12px; color: var(--text-muted); text-align: right; }
.ticker-header { display: grid; grid-template-columns: 1.4fr 1fr; gap: 18px; }
.ticker-company { font-size: 28px; font-weight: 700; letter-spacing: -0.04em; }
.ticker-symbol { font-size: 12px; letter-spacing: 0.16em; text-transform: uppercase; color: #5bc0ff; }
.meta-row, .chip-row, .action-list { display: flex; gap: 8px; flex-wrap: wrap; }
.section-metric-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }
.mini-stat {
  padding: 12px; border-radius: 14px; background: rgba(18,34,49,0.82); border: 1px solid rgba(127,150,173,0.14); display: grid; gap: 6px;
}
.mini-stat-label { font-size: 10px; text-transform: uppercase; letter-spacing: 0.10em; color: #667b91; }
.mini-stat-value { font-size: 22px; font-weight: 700; }
.terminal-caption { color: var(--text-muted); font-size: 12px; }
@media (max-width: 1120px) {
  .hero-grid, .two-col, .three-col, .kpi-strip, .ticker-header { grid-template-columns: 1fr; }
  .allocation-row { grid-template-columns: 1fr; }
}
"""
