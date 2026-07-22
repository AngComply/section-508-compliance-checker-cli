"""Unit tests for the focus-visibility and icon-contrast checks (no browser).

These drive the checks with synthetic Selenium-style records, so they run in CI
without Chrome. Live browser coverage is in test_selenium_integration.py.
"""

from __future__ import annotations

from section508checker.checks.base import Severity
from section508checker.checks.focus import FocusVisibleCheck
from section508checker.checks.graphics import IconContrastCheck


def _focus(**kwargs) -> dict:
    base = {
        "outlineStyle": "none",
        "outlineWidth": "0px",
        "outlineColor": "rgb(0, 0, 0)",
        "boxShadow": "none",
        "snippet": "<button>x</button>",
    }
    base.update(kwargs)
    return base


def test_focus_missing_indicator_flagged():
    check = FocusVisibleCheck()
    check.focus_states = [_focus(outlineStyle="none", boxShadow="none")]
    findings = check.run(None)
    assert len(findings) == 1
    assert findings[0].criterion == "2.4.7"
    assert findings[0].severity is Severity.WARNING


def test_focus_visible_outline_passes():
    check = FocusVisibleCheck()
    check.focus_states = [_focus(outlineStyle="solid", outlineWidth="3px")]
    assert check.run(None) == []


def test_focus_default_ring_auto_passes():
    check = FocusVisibleCheck()
    # The browser default focus ring computes outline-style: auto.
    check.focus_states = [_focus(outlineStyle="auto", outlineWidth="auto")]
    assert check.run(None) == []


def test_focus_box_shadow_indicator_passes():
    check = FocusVisibleCheck()
    check.focus_states = [_focus(boxShadow="rgb(0, 90, 173) 0px 0px 0px 3px")]
    assert check.run(None) == []


def test_focus_transparent_outline_is_not_visible():
    check = FocusVisibleCheck()
    check.focus_states = [
        _focus(outlineStyle="solid", outlineWidth="2px", outlineColor="rgba(0,0,0,0)")
    ]
    assert len(check.run(None)) == 1


def test_focus_no_data_returns_nothing():
    assert FocusVisibleCheck().run(None) == []


def _graphic(fill="rgb(0,0,0)", stroke="none", background="rgb(255,255,255)"):
    return {
        "fill": fill,
        "stroke": stroke,
        "background": background,
        "snippet": '<svg role="img">…</svg>',
    }


def test_icon_low_contrast_flagged():
    check = IconContrastCheck()
    # Light grey icon on white -> ~1.6:1 -> flagged.
    check.graphic_styles = [_graphic(fill="rgb(200, 200, 200)")]
    findings = check.run(None)
    assert len(findings) == 1
    assert findings[0].criterion == "1.4.11"
    assert findings[0].severity is Severity.WARNING


def test_icon_sufficient_contrast_passes():
    check = IconContrastCheck()
    check.graphic_styles = [_graphic(fill="rgb(0, 0, 0)")]
    assert check.run(None) == []


def test_icon_falls_back_to_stroke_when_fill_none():
    check = IconContrastCheck()
    check.graphic_styles = [_graphic(fill="none", stroke="rgb(210, 210, 210)")]
    assert len(check.run(None)) == 1


def test_icon_skips_when_background_unresolved():
    check = IconContrastCheck()
    check.graphic_styles = [_graphic(background="")]
    assert check.run(None) == []


def test_icon_no_data_returns_nothing():
    assert IconContrastCheck().run(None) == []
