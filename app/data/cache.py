from __future__ import annotations

import pickle
import time
from pathlib import Path
from typing import Any


class FileCache:
    def __init__(self, cache_dir: str | Path, default_ttl_seconds: int = 3600) -> None:
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.default_ttl_seconds = default_ttl_seconds

    def _path_for(self, key: str) -> Path:
        safe_key = "".join(char if char.isalnum() or char in {"-", "_"} else "_" for char in key)
        return self.cache_dir / f"{safe_key}.pkl"

    def get(self, key: str, ttl_seconds: int | None = None) -> Any | None:
        path = self._path_for(key)
        if not path.exists():
            return None
        with path.open("rb") as handle:
            payload = pickle.load(handle)
        ttl = self.default_ttl_seconds if ttl_seconds is None else ttl_seconds
        if time.time() - payload["stored_at"] > ttl:
            return None
        return payload["value"]

    def set(self, key: str, value: Any) -> Any:
        path = self._path_for(key)
        with path.open("wb") as handle:
            pickle.dump({"stored_at": time.time(), "value": value}, handle)
        return value

    def get_or_set(self, key: str, factory, ttl_seconds: int | None = None, force_refresh: bool = False) -> Any:
        if not force_refresh:
            cached = self.get(key, ttl_seconds=ttl_seconds)
            if cached is not None:
                return cached
        return self.set(key, factory())

    def clear(self) -> None:
        for path in self.cache_dir.glob("*.pkl"):
            path.unlink()
