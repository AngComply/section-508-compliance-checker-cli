"""Frame title checks (WCAG 4.1.2 Name, Role, Value; 2.4.1 Bypass Blocks)."""
from __future__ import annotations

from typing import TYPE_CHECKING

from .base import Check, Finding, Severity, element_snippet
from .naming import attr_text, has_aria_name, is_hidden

if TYPE_CHECKING:  # pragma: no cover - typing only
    from bs4 import BeautifulSoup


class FrameTitleCheck(Check):
    """Flag ``<iframe>`` / ``<frame>`` elements without an accessible name.

    Without a ``title`` (or equivalent ARIA name), a screen reader announces
    only "frame", leaving users unable to tell embedded regions apart.
    """

    id = "frame-title"
    criterion = "4.1.2"
    criterion_name = "Name, Role, Value"
    description = "Frames must have a descriptive title attribute."

    def run(self, soup: "BeautifulSoup") -> list[Finding]:
        findings: list[Finding] = []
        for frame in soup.find_all(["iframe", "frame"]):
            if is_hidden(frame):
                continue
            if attr_text(frame, "title") or has_aria_name(frame):
                continue
            findings.append(
                self._finding(
                    Severity.ERROR,
                    f"<{frame.name}> has no title attribute, so its purpose is "
                    "not announced.",
                    'Add a title describing the frame, e.g. title="Payment '
                    'form".',
                    element_snippet(frame),
                )
            )
        return findings
