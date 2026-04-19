"""Importing the app module exercises layout wiring and create_app (coverage for main)."""

from __future__ import annotations


def test_main_module_imports():
    import app.main as main_module

    assert main_module.app is not None
    assert main_module.server is not None
    assert main_module.create_app is not None
