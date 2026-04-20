from __future__ import annotations

from pathlib import Path

import pytest

from app.config import load_config


def test_load_config_defaults():
    cfg = load_config()
    assert cfg.dashboard.symbol == "BTC-USD"
    assert cfg.dashboard.default_range == "90D"
    assert cfg.dashboard.moving_averages == (20, 50, 200)
    assert cfg.dashboard.refresh_interval_seconds == 0
    assert cfg.cache.default_ttl_seconds == 900
    assert cfg.cache.market_ttl_seconds == 900


def test_load_config_invalid_yaml(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    import app.config as cfgmod

    bad = tmp_path / "settings.yaml"
    bad.write_text("{broken", encoding="utf-8")
    monkeypatch.setattr(cfgmod, "CONFIG_DIR", tmp_path)
    with pytest.raises(Exception):
        load_config()


def test_load_config_mapping_required(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    import app.config as cfgmod

    bad = tmp_path / "settings.yaml"
    bad.write_text("42\n", encoding="utf-8")
    monkeypatch.setattr(cfgmod, "CONFIG_DIR", tmp_path)
    with pytest.raises(ValueError, match="Expected mapping"):
        load_config()
