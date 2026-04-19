from pathlib import Path

from app.data.cache import FileCache


def test_cache_round_trip(tmp_path: Path):
    cache = FileCache(tmp_path, default_ttl_seconds=60)
    cache.set("key", {"value": 1})
    assert cache.get("key") == {"value": 1}


def test_cache_get_or_set_uses_factory_once(tmp_path: Path):
    cache = FileCache(tmp_path, default_ttl_seconds=60)
    calls = {"count": 0}

    def factory():
        calls["count"] += 1
        return "value"

    assert cache.get_or_set("demo", factory) == "value"
    assert cache.get_or_set("demo", factory) == "value"
    assert calls["count"] == 1
