from __future__ import annotations

from app.components.theme import plotly_template


def test_plotly_template_singleton():
    a = plotly_template()
    b = plotly_template()
    assert a is b
