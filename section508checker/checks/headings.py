"""Heading-structure checks (WCAG 1.3.1 Info and Relationships,
2.4.6 Headings and Labels)."""
from __future__ import annotations

from typing import TYPE_CHECKING

from .base import Check, Finding, Severity, element_snippet
from .naming import is_hidden

if TYPE_CHECKING:  # pragma: no cover - typing only
    from bs4 import BeautifulSoup

_HEADING_TAGS = ["h1", "h2", "h3", "h4", "h5", "h6"]


class HeadingStructureCheck(Check):
    """Flag missing, empty, or improperly nested headings.

    Reports three conditions:
      * a heading whose text content is empty,
      * a first heading that is not ``<h1>``,
      * a skipped heading level (e.g. ``<h2>`` followed directly by ``<h4>``).
    """

    id = "heading-structure"
    criterion = "1.3.1"
    criterion_name = "Info and Relationships"
    description = "Headings must be non-empty and nested without skipping levels."

    def run(self, soup: "BeautifulSoup") -> list[Finding]:
        headings = [
            h for h in soup.find_all(_HEADING_TAGS) if not is_hidden(h)
        ]
        if not headings:
            return []

        findings: list[Finding] = []
        previous_level: int | None = None

        for heading in headings:
            level = int(heading.name[1])

            if not heading.get_text(strip=True):
                findings.append(
                    self._finding(
                        Severity.WARNING,
                        f"<{heading.name}> heading is empty.",
                        "Remove the empty heading or give it meaningful text.",
                        element_snippet(heading),
                    )
                )

            if previous_level is None:
                if level != 1:
                    findings.append(
                        self._finding(
                            Severity.WARNING,
                            f"First heading on the page is <{heading.name}>; "
                            "pages should begin their outline at <h1>.",
                            "Start the heading hierarchy with a single <h1>.",
                            element_snippet(heading),
                        )
                    )
            elif level > previous_level + 1:
                findings.append(
                    self._finding(
                        Severity.WARNING,
                        f"Heading level skips from <h{previous_level}> to "
                        f"<{heading.name}>.",
                        "Do not skip heading levels; use the next sequential "
                        "level so the outline stays intact.",
                        element_snippet(heading),
                    )
                )

            previous_level = level

        return findings
