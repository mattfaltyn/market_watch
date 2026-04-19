from __future__ import annotations

import pandas as pd

from app.config import load_config
from app.routing import dispatch_page, dispatch_page_safe, refresh_state_payload
from tests.routing_fake import RoutingFakeClient


def test_dispatch_overview_default_path():
    cfg = load_config()
    out = dispatch_page("/", {"refresh": 0}, "url", client=RoutingFakeClient(), config=cfg)
    assert out is not None


def test_dispatch_markets():
    cfg = load_config()
    out = dispatch_page("/markets", {"refresh": 0}, "url", client=RoutingFakeClient(), config=cfg)
    assert out is not None


def test_dispatch_market_watch_redirects():
    cfg = load_config()
    out = dispatch_page("/market-watch", {"refresh": 0}, "url", client=RoutingFakeClient(), config=cfg)
    assert out is not None


def test_dispatch_watchlist():
    cfg = load_config()
    out = dispatch_page("/watchlist", {"refresh": 0}, "url", client=RoutingFakeClient(), config=cfg)
    assert out is not None


def test_dispatch_ticker_spy():
    cfg = load_config()
    out = dispatch_page("/ticker/SPY", {"refresh": 0}, "url", client=RoutingFakeClient(), config=cfg)
    assert out is not None


def test_dispatch_unsupported_ticker():
    cfg = load_config()
    out = dispatch_page("/ticker/INVALID", {"refresh": 0}, "url", client=RoutingFakeClient(), config=cfg)
    assert out is not None


def test_force_refresh_when_refresh_triggered():
    cfg = load_config()
    dispatch_page("/", {"refresh": 1}, "refresh-state", client=RoutingFakeClient(), config=cfg)


def test_refresh_state_payload_branches():
    assert refresh_state_payload(None, None) == {"refresh": 0, "last": 0}
    assert refresh_state_payload(3, {"last": 7}) == {"refresh": 3, "last": 7}


def test_dispatch_safe_maps_exception():
    cfg = load_config()
    out = dispatch_page_safe("/", {"refresh": 0}, "url", client=RoutingFakeClient(boom=True), config=cfg)
    assert out is not None
