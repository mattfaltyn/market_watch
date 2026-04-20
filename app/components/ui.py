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
  --bg: #071018;
  --bg-accent: #0b1824;
  --shell: rgba(13, 24, 35, 0.92);
  --panel: #111f2d;
  --panel-2: #162737;
  --panel-3: #1c3143;
  --text: #f3f7fb;
  --text-soft: #ccd6e0;
  --text-muted: #a8b6c5;
  --text-faint: #7f90a3;
  --border: rgba(140, 164, 191, 0.18);
  --border-strong: rgba(140, 164, 191, 0.28);
  --cyan: #45b7d9;
  --cyan-soft: rgba(69, 183, 217, 0.14);
  --green: #3fd07a;
  --green-soft: rgba(63, 208, 122, 0.12);
  --amber: #f6b55f;
  --amber-soft: rgba(246, 181, 95, 0.12);
  --red: #ff6b6b;
  --red-soft: rgba(255, 107, 107, 0.12);
  --shadow-shell: 0 22px 48px rgba(0, 0, 0, 0.36);
  --shadow-panel: 0 16px 28px rgba(0, 0, 0, 0.22);
}
* { box-sizing: border-box; }
html { background: var(--bg); }
body {
  margin: 0;
  font-family: "IBM Plex Sans", "Avenir Next", sans-serif;
  background:
    radial-gradient(circle at top left, rgba(69, 183, 217, 0.08), transparent 30%),
    radial-gradient(circle at top right, rgba(246, 181, 95, 0.06), transparent 24%),
    linear-gradient(180deg, #08121b 0%, var(--bg) 24%, #050c13 100%);
  color: var(--text);
}
a { color: var(--text-soft); text-decoration: none; font-weight: 600; }

.app-shell { min-height: 100vh; padding: 18px 18px 54px; }
.app-frame {
  margin: 0 auto;
  max-width: 1480px;
  background: var(--shell);
  border: 1px solid var(--border-strong);
  backdrop-filter: blur(18px);
  box-shadow: var(--shadow-shell);
  position: sticky;
  top: 16px;
  z-index: 10;
}
.shell-stack { gap: 14px; }
.shell-top {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 18px;
  flex-wrap: wrap;
}
.shell-brand {
  display: grid;
  gap: 8px;
  min-width: min(100%, 520px);
}
.shell-kicker {
  font-size: 11px;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: var(--cyan);
}
.shell-title-row {
  display: flex;
  align-items: flex-end;
  gap: 14px;
  flex-wrap: wrap;
}
.shell-title {
  margin: 0;
  font-size: clamp(28px, 4vw, 38px);
  line-height: 0.96;
  letter-spacing: -0.05em;
  color: var(--text);
}
.shell-subtitle {
  font-size: 14px;
  color: var(--text-muted);
  max-width: 720px;
}
.shell-status {
  display: flex;
  gap: 14px;
  align-items: stretch;
  flex-wrap: wrap;
  margin-left: auto;
}
.status-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(120px, 1fr));
  gap: 10px;
  min-width: min(100%, 430px);
}
.status-pill {
  padding: 10px 12px;
  border-radius: 14px;
  border: 1px solid var(--border);
  background: rgba(255, 255, 255, 0.03);
  display: grid;
  gap: 4px;
}
.status-label {
  font-size: 10px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--text-faint);
}
.status-value {
  color: var(--text-soft);
  font-size: 13px;
  font-weight: 600;
}
.refresh-button {
  border: 1px solid rgba(69, 183, 217, 0.32);
  border-radius: 14px;
  background: linear-gradient(180deg, rgba(69, 183, 217, 0.20), rgba(69, 183, 217, 0.10));
  color: var(--text);
  padding: 0 18px;
  min-height: 46px;
  font-weight: 700;
  font-size: 14px;
  cursor: pointer;
  transition: transform 120ms ease, border-color 120ms ease, background 120ms ease;
}
.refresh-button:hover {
  transform: translateY(-1px);
  border-color: rgba(69, 183, 217, 0.46);
  background: linear-gradient(180deg, rgba(69, 183, 217, 0.24), rgba(69, 183, 217, 0.12));
}
.shell-nav {
  display: inline-flex;
  gap: 8px;
  padding: 6px;
  border-radius: 14px;
  border: 1px solid var(--border);
  background: rgba(255, 255, 255, 0.03);
  flex-wrap: wrap;
}
.nav-link { text-decoration: none; }
.nav-pill {
  padding: 10px 14px;
  border-radius: 10px;
  color: var(--text-muted);
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  border: 1px solid transparent;
  transition: background 120ms ease, color 120ms ease, border-color 120ms ease;
}
.nav-pill:hover {
  color: var(--text-soft);
  background: rgba(255, 255, 255, 0.04);
}
.nav-pill.is-active {
  color: var(--text);
  background: rgba(69, 183, 217, 0.14);
  border-color: rgba(69, 183, 217, 0.24);
  box-shadow: inset 0 0 0 1px rgba(69, 183, 217, 0.14);
}

.page-body-wrap { padding: 20px 0 0; }
.page-body {
  max-width: 1480px;
  margin: 0 auto;
  display: grid;
  gap: 16px;
}
.hero-grid, .two-col, .info-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; }
.three-col { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 16px; }
.four-col, .kpi-strip { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 14px; }
.signal-grid, .proxy-grid, .chart-wall, .benchmark-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 14px;
}
.section.panel {
  background: linear-gradient(180deg, rgba(21, 34, 47, 0.98), rgba(17, 31, 45, 0.98));
  border: 1px solid var(--border);
  box-shadow: var(--shadow-panel);
}
.section-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 12px;
}
.section-heading {
  display: grid;
  gap: 4px;
}
.section-kicker {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--cyan);
}
.section-title {
  font-size: 18px;
  font-weight: 700;
  color: var(--text);
}
.section-subtitle {
  font-size: 13px;
  color: var(--text-muted);
}
.section-body {
  display: grid;
  gap: 12px;
}
.section.panel.variant-inset {
  background: linear-gradient(180deg, rgba(25, 41, 57, 0.96), rgba(20, 34, 47, 0.96));
}
.section.panel.variant-shell {
  background: linear-gradient(180deg, rgba(23, 39, 55, 0.98), rgba(18, 32, 45, 0.98));
  border-color: var(--border-strong);
}

.overview-hero {
  padding: 22px;
  border-radius: 18px;
  border: 1px solid var(--border-strong);
  background:
    linear-gradient(135deg, rgba(69, 183, 217, 0.08), transparent 24%),
    linear-gradient(180deg, rgba(24, 42, 58, 0.98), rgba(17, 31, 45, 0.98));
  box-shadow: var(--shadow-panel);
  display: grid;
  gap: 18px;
}
.hero-main {
  display: grid;
  grid-template-columns: minmax(0, 1.5fr) minmax(220px, 0.9fr);
  gap: 18px;
  align-items: stretch;
}
.hero-summary {
  display: grid;
  gap: 14px;
}
.hero-regime-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.hero-regime {
  margin: 0;
  font-size: clamp(34px, 5vw, 48px);
  line-height: 0.92;
  letter-spacing: -0.05em;
}
.hero-copy {
  color: var(--text-soft);
  font-size: 15px;
  max-width: 820px;
}
.hero-detail-row, .meta-row, .chip-row, .action-list {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.hero-support-text {
  color: var(--text-muted);
  font-size: 13px;
}
.hero-gauge {
  display: grid;
  align-content: space-between;
  gap: 12px;
  padding: 16px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid var(--border);
}
.hero-gauge-label {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--text-faint);
}
.hero-gauge-value {
  font-size: 34px;
  font-weight: 700;
  line-height: 0.95;
}
.hero-gauge-caption {
  font-size: 13px;
  color: var(--text-muted);
}
.hero-band {
  height: 10px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.06);
  overflow: hidden;
}
.hero-band-fill {
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, var(--cyan), #72d5ea);
}

.metric-card {
  min-height: 124px;
  background: linear-gradient(180deg, rgba(20, 34, 47, 0.98), rgba(17, 31, 45, 0.98));
  border: 1px solid var(--border);
  box-shadow: var(--shadow-panel);
}
.metric-card-shell {
  display: grid;
  gap: 12px;
  height: 100%;
}
.metric-card-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 8px;
}
.metric-card-label {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--text-faint);
}
.metric-card-icon {
  color: var(--text-faint);
  font-size: 14px;
}
.metric-card-value {
  font-size: 30px;
  line-height: 0.95;
  font-weight: 700;
  color: var(--text);
}
.metric-card-delta {
  font-size: 13px;
  color: var(--text-muted);
}
.metric-card.emphasis-high {
  border-color: rgba(69, 183, 217, 0.28);
}
.metric-card.metric-compact .metric-card-value {
  font-size: 24px;
}
.metric-sparkline-placeholder {
  height: 34px;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.02);
}

.market-badge {
  border: 1px solid transparent;
  letter-spacing: 0.08em;
  font-weight: 700;
}
.market-badge.badge-tone-market { background: rgba(69, 183, 217, 0.12); color: #84dcf4; border-color: rgba(69, 183, 217, 0.18); }
.market-badge.badge-tone-warning, .market-badge.badge-tone-rates { background: var(--amber-soft); color: #ffca8a; border-color: rgba(246, 181, 95, 0.18); }
.market-badge.badge-tone-positive, .market-badge.badge-tone-bullish { background: var(--green-soft); color: #8ce4af; border-color: rgba(63, 208, 122, 0.18); }
.market-badge.badge-tone-negative, .market-badge.badge-tone-bearish { background: var(--red-soft); color: #ffaaaa; border-color: rgba(255, 107, 107, 0.18); }
.market-badge.badge-tone-neutral_state { background: rgba(147, 166, 188, 0.10); color: #c9d3dc; border-color: rgba(147, 166, 188, 0.16); }

.stat-chip {
  display: grid;
  gap: 5px;
  padding: 11px 12px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid var(--border);
  min-width: 108px;
}
.stat-chip-label, .mini-panel-label, .delta-symbol, .heat-label, .allocation-row-label, .mini-stat-label {
  font-size: 10px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--text-faint);
}
.stat-chip-value { font-size: 13px; color: var(--text-soft); font-weight: 600; }
.tone-positive, .tone-bullish { border-color: rgba(63, 208, 122, 0.30); }
.tone-negative, .tone-bearish { border-color: rgba(255, 107, 107, 0.30); }
.tone-warning, .tone-rates { border-color: rgba(246, 181, 95, 0.30); }
.tone-market { border-color: rgba(69, 183, 217, 0.30); }
.tone-neutral_state { border-color: rgba(147, 166, 188, 0.26); }

.signal-meter { display: grid; gap: 7px; }
.signal-meter-head { display: flex; justify-content: space-between; color: var(--text-muted); font-size: 11px; }
.signal-meter-track {
  position: relative;
  height: 10px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.05);
  overflow: visible;
}
.signal-meter-thumb {
  position: absolute;
  top: 1px;
  width: 14px;
  height: 8px;
  border-radius: 999px;
  transform: translateX(-50%);
}
.signal-meter-thumb.tone-market { background: var(--cyan); }
.signal-meter-thumb.tone-rates, .signal-meter-thumb.tone-warning { background: var(--amber); }
.signal-meter-thumb.tone-positive, .signal-meter-thumb.tone-bullish { background: var(--green); }
.signal-meter-thumb.tone-negative, .signal-meter-thumb.tone-bearish { background: var(--red); }
.signal-meter-thumb.tone-neutral_state { background: #93a6bc; }

.macro-quadrant { position: relative; min-height: 300px; }
.quadrant-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; }
.quadrant-cell {
  min-height: 126px;
  padding: 15px;
  border-radius: 16px;
  border: 1px solid var(--border);
  background: linear-gradient(180deg, rgba(32, 49, 67, 0.96), rgba(24, 39, 54, 0.96));
  display: grid;
  align-content: end;
  gap: 8px;
}
.quadrant-cell.is-active {
  border-color: rgba(69, 183, 217, 0.42);
  box-shadow: inset 0 0 0 1px rgba(69, 183, 217, 0.24);
}
.quadrant-cell-label {
  font-size: 15px;
  font-weight: 700;
  letter-spacing: 0.08em;
}
.quadrant-cell-text { color: var(--text-muted); font-size: 12px; }
.quadrant-label { position: absolute; font-size: 10px; letter-spacing: 0.12em; text-transform: uppercase; color: var(--text-faint); }
.x-axis-pos { right: 18px; bottom: -4px; }
.x-axis-neg { left: 18px; bottom: -4px; }
.y-axis-pos { top: -6px; right: 22px; }
.y-axis-neg { bottom: 28px; left: -2px; transform: rotate(-90deg); transform-origin: left bottom; }
.quadrant-point {
  position: absolute;
  width: 14px;
  height: 14px;
  border-radius: 999px;
  background: var(--amber);
  border: 2px solid var(--bg);
  box-shadow: 0 0 0 4px rgba(246, 181, 95, 0.20);
  z-index: 2;
}
.quadrant-point-pulse { animation: quadrant-pulse 3s ease-in-out infinite; }
@keyframes quadrant-pulse {
  0%, 100% { box-shadow: 0 0 0 4px rgba(246, 181, 95, 0.20); }
  50% { box-shadow: 0 0 0 7px rgba(246, 181, 95, 0.30); }
}
.quadrant-summary { margin-top: 14px; display: flex; gap: 8px; flex-wrap: wrap; }

.benchmark-tile, .delta-event, .heat-cell, .mini-stat, .table-note {
  background: linear-gradient(180deg, rgba(24, 39, 54, 0.96), rgba(20, 34, 47, 0.96));
  border: 1px solid var(--border);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.02);
}
.benchmark-tile {
  min-height: 100px;
  display: grid;
  gap: 8px;
}
.benchmark-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
}
.benchmark-symbol {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.10em;
  text-transform: uppercase;
  color: var(--text-soft);
}
.benchmark-price {
  font-size: 24px;
  line-height: 1;
  font-weight: 700;
}
.benchmark-delta {
  color: var(--text-muted);
  font-size: 13px;
}
.benchmark-note { color: var(--text-faint); font-size: 11px; }

.delta-strip { display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); gap: 12px; }
.delta-event {
  padding: 13px;
  border-radius: 14px;
  display: grid;
  gap: 6px;
}
.delta-field {
  font-size: 22px;
  font-weight: 700;
  line-height: 1;
}
.delta-transition { font-size: 13px; color: var(--text-muted); }
.delta-strip.empty, .empty-state {
  padding: 14px;
  border-radius: 14px;
  border: 1px dashed var(--border);
  background: rgba(255, 255, 255, 0.02);
  color: var(--text-muted);
  font-size: 12px;
}

.heatstrip { display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 10px; }
.heat-cell {
  padding: 12px;
  border-radius: 13px;
  display: grid;
  gap: 6px;
}
.heat-value { font-size: 18px; font-weight: 700; }

.warning-rack { display: grid; gap: 8px; }
.warning-title {
  font-size: 11px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: #ffca8a;
}
.warning-item, .guidance-item {
  border-radius: 12px;
  padding: 11px 12px;
  font-size: 12px;
}
.warning-item {
  background: rgba(246, 181, 95, 0.10);
  border: 1px solid rgba(246, 181, 95, 0.18);
  color: #ffd8a8;
}
.guidance-item {
  background: rgba(69, 183, 217, 0.08);
  border: 1px solid rgba(69, 183, 217, 0.16);
  color: var(--text-soft);
}
.terminal-caption { color: var(--text-muted); font-size: 12px; }

.sparkline .js-plotly-plot, .chart .js-plotly-plot { width: 100% !important; }
.chart .plotly .main-svg, .sparkline .plotly .main-svg { border-radius: 14px; }
.section.panel .chart .js-plotly-plot > div { background: transparent !important; }

.sleeve-card {
  padding: 16px;
  display: grid;
  gap: 12px;
  border-radius: 16px;
  border: 1px solid var(--border);
  background: linear-gradient(180deg, rgba(24, 39, 54, 0.96), rgba(20, 34, 47, 0.96));
}
.sleeve-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 10px;
}
.sleeve-head-left {
  display: flex;
  align-items: center;
  gap: 10px;
}
.symbol-dot, .legend-dot {
  width: 10px;
  height: 10px;
  border-radius: 999px;
}
.sleeve-symbol { font-size: 16px; font-weight: 700; }
.sleeve-main-value {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: baseline;
}
.sleeve-actual { font-size: 28px; font-weight: 700; }
.sleeve-target { color: var(--text-muted); font-size: 13px; }
.sleeve-bars, .sleeve-footer { display: grid; gap: 10px; }

.allocation-band { display: grid; gap: 14px; }
.allocation-legend { display: flex; gap: 12px; flex-wrap: wrap; }
.legend-item { display: flex; align-items: center; gap: 8px; color: var(--text-muted); font-size: 12px; }
.allocation-rows { display: grid; gap: 12px; }
.allocation-row { display: grid; grid-template-columns: 80px 1fr minmax(180px, 260px); gap: 12px; align-items: center; }
.allocation-track {
  display: flex;
  height: 18px;
  border-radius: 999px;
  overflow: hidden;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(140, 164, 191, 0.12);
}
.allocation-segment { height: 100%; }
.allocation-row-values { font-size: 12px; color: var(--text-muted); text-align: right; }

.data-table-panel {
  background: linear-gradient(180deg, rgba(18, 31, 44, 0.98), rgba(15, 27, 38, 0.98));
  border: 1px solid var(--border);
  overflow: hidden;
  box-shadow: var(--shadow-panel);
}
.table-shell {
  overflow-x: auto;
  border-radius: 14px;
}
.data-table {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  font-size: 12px;
  min-width: 760px;
}
.data-table thead th {
  position: sticky;
  top: 0;
  z-index: 1;
  padding: 12px 14px;
  background: #182b3c;
  color: var(--text-faint);
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  text-align: left;
  border-bottom: 1px solid var(--border-strong);
}
.data-table tbody td {
  padding: 12px 14px;
  border-bottom: 1px solid rgba(140, 164, 191, 0.10);
  color: var(--text-soft);
}
.data-table tbody tr:nth-child(even) td { background: rgba(255, 255, 255, 0.015); }
.data-table tbody tr:hover td { background: rgba(69, 183, 217, 0.06); }
.table-link {
  color: #84dcf4;
  font-weight: 700;
  letter-spacing: 0.04em;
}

.ticker-header { display: grid; grid-template-columns: 1.35fr 1fr; gap: 16px; }
.ticker-title-block { display: grid; gap: 10px; }
.ticker-company {
  font-size: clamp(26px, 4vw, 34px);
  font-weight: 700;
  line-height: 0.96;
  letter-spacing: -0.04em;
}
.ticker-symbol {
  font-size: 11px;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: var(--cyan);
}
.section-metric-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }
.mini-stat {
  padding: 12px;
  border-radius: 14px;
  display: grid;
  gap: 6px;
}
.mini-stat-value { font-size: 22px; font-weight: 700; }

.watchlist-summary {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  flex-wrap: wrap;
}
.watchlist-note {
  color: var(--text-muted);
  font-size: 13px;
}

@media (max-width: 1120px) {
  .hero-main, .hero-grid, .two-col, .three-col, .kpi-strip, .ticker-header, .four-col { grid-template-columns: 1fr; }
  .allocation-row { grid-template-columns: 1fr; }
}
@media (max-width: 860px) {
  .app-shell { padding: 12px 12px 40px; }
  .app-frame { position: static; }
  .status-grid { grid-template-columns: 1fr; min-width: 100%; }
  .shell-status { width: 100%; }
  .refresh-button { width: 100%; }
}
"""
