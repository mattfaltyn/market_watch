from __future__ import annotations

from pathlib import Path

from app.data.cache import FileCache


def test_file_cache_roundtrip(tmp_path: Path):
    cache = FileCache(tmp_path / "c", default_ttl_seconds=3600)
    assert cache.get("k") is None
    cache.set("k", {"a": 1})
    assert cache.get("k") == {"a": 1}


def test_file_cache_get_or_set_force(tmp_path: Path):
    cache = FileCache(tmp_path / "c2", default_ttl_seconds=3600)
    calls = {"n": 0}

    def factory():
        calls["n"] += 1
        return calls["n"]

    assert cache.get_or_set("x", factory) == 1
    assert cache.get_or_set("x", factory) == 1
    assert cache.get_or_set("x", factory, force_refresh=True) == 2


def test_file_cache_clear(tmp_path: Path):
    cache = FileCache(tmp_path / "c3", default_ttl_seconds=3600)
    cache.set("a", 1)
    cache.clear()
    assert cache.get("a") is None
