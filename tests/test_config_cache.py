from __future__ import annotations

from pathlib import Path

import pytest

from app.config import AppConfig, _load_yaml, load_config


def test_load_config_reads_project_settings():
    cfg = load_config()
    assert isinstance(cfg, AppConfig)
    assert cfg.sleeves.get("equity") == "SPY"


def test_load_yaml_invalid_root(tmp_path: Path):
    path = tmp_path / "bad.yaml"
    path.write_text("- item\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Expected mapping"):
        _load_yaml(path)


def test_app_config_properties_defaults():
    cfg = AppConfig(kiss={}, chart_windows={}, cache={}, alert_thresholds={})
    assert cfg.sleeves == {}
    assert cfg.base_weights == {}
    assert cfg.regime_rules == {}
    assert cfg.vams_multipliers == {}
    assert cfg.regime_inputs == {}
    assert cfg.market_watch_symbols == []
    assert cfg.sleeve_symbols == []


def test_market_watch_symbols_normalizes_case():
    cfg = AppConfig(
        kiss={"market_watch_symbols": ["spy", "qqq"]},
        chart_windows={},
        cache={},
        alert_thresholds={},
    )
    assert cfg.market_watch_symbols == ["SPY", "QQQ"]


def test_cache_ttl_expired(monkeypatch, tmp_path: Path):
    import app.data.cache as cache_mod

    clock = {"t": 1000.0}

    def fake_time():
        return clock["t"]

    monkeypatch.setattr(cache_mod.time, "time", fake_time)
    from app.data.cache import FileCache

    c = FileCache(tmp_path, default_ttl_seconds=60)
    c.set("k", "v")
    assert c.get("k") == "v"
    clock["t"] += 120
    assert c.get("k") is None


def test_cache_get_or_set_force_refresh(tmp_path: Path):
    from app.data.cache import FileCache

    c = FileCache(tmp_path, default_ttl_seconds=3600)
    calls = {"n": 0}

    def factory():
        calls["n"] += 1
        return calls["n"]

    assert c.get_or_set("a", factory) == 1
    assert c.get_or_set("a", factory) == 1
    assert c.get_or_set("a", factory, force_refresh=True) == 2


def test_cache_clear(tmp_path: Path):
    from app.data.cache import FileCache

    c = FileCache(tmp_path)
    c.set("a", 1)
    c.clear()
    assert c.get("a") is None
