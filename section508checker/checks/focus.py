"""Keyboard focus-visibility check (WCAG 2.4.7 Focus Visible).

Consumes the focus-state records collected by the Selenium backend, which tabs
through the page with the keyboard so ``:focus-visible`` rules apply. An element
is flagged only when, in its focused state, it shows no visible indicator at all
(no outline and no box-shadow) — the classic ``outline: none`` regression. The
browser's default focus ring computes ``outline-style: auto`` and is treated as
visible, so unstyled elements are not falsely flagged.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .base import Check, Finding, Severity
from .color import parse_color

if TYPE_CHECKING:  # pragma: no cover - typing only
    from bs4 import BeautifulSoup


def _outline_visible(state: dict) -> bool:
    style = str(state.get("outlineStyle", "")).strip().lower()
    if style in ("", "none", "hidden"):
        return False
    if style == "auto":
        return True  # browser default focus ring
    try:
        width = float(str(state.get("outlineWidth", "0")).rstrip("px").strip() or 0)
    except ValueError:
        width = 0.0
    if width <= 0:
        return False
    color = parse_color(str(state.get("outlineColor", "")))
    return not (color is not None and color[3] <= 0)


def _has_focus_indicator(state: dict) -> bool:
    if _outline_visible(state):
        return True
    box_shadow = str(state.get("boxShadow", "none")).strip().lower()
    return box_shadow not in ("", "none")


class FocusVisibleCheck(Check):
    """Flag interactive elements with no visible keyboard focus indicator."""

    id = "focus-visible"
    criterion = "2.4.7"
    criterion_name = "Focus Visible"
    description = "Focusable elements must show a visible keyboard focus indicator."

    #: Focus-state records injected by the runner (Selenium backend only).
    focus_states: list[dict] | None = None

    def run(self, soup: "BeautifulSoup") -> list[Finding]:
        if self.focus_states is None:
            return []
        findings: list[Finding] = []
        for state in self.focus_states:
            if _has_focus_indicator(state):
                continue
            snippet = " ".join(str(state.get("snippet", ""))[:120].split())
            findings.append(
                self._finding(
                    Severity.WARNING,
                    "Element has no visible focus indicator when focused with the "
                    "keyboard, so keyboard users cannot see where focus is.",
                    "Provide a visible :focus-visible style (a clear outline or "
                    "box-shadow); never remove the outline without a replacement.",
                    snippet,
                )
            )
        return findings
