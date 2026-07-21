"""Image accessibility checks (WCAG 1.1.1 Non-text Content)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .base import Check, Finding, Severity, element_snippet
from .naming import is_hidden

if TYPE_CHECKING:  # pragma: no cover - typing only
    from bs4 import BeautifulSoup


class ImageAltTextCheck(Check):
    """Flag ``<img>`` elements that lack an ``alt`` attribute.

    A missing ``alt`` attribute is a failure: assistive technology falls back to
    announcing the file name or nothing at all. An explicitly empty ``alt=""``
    is valid and intentional (it marks a decorative image), so it passes.
    """

    id = "img-alt"
    criterion = "1.1.1"
    criterion_name = "Non-text Content"
    description = 'Images must have an alt attribute (alt="" if decorative).'

    def run(self, soup: "BeautifulSoup") -> list[Finding]:
        findings: list[Finding] = []
        for img in soup.find_all("img"):
            if is_hidden(img):
                continue
            if img.has_attr("alt"):
                continue  # alt present (including intentional alt="")
            findings.append(
                self._finding(
                    Severity.ERROR,
                    "Image is missing an alt attribute.",
                    'Add descriptive alt text, or alt="" if the image is '
                    "purely decorative.",
                    element_snippet(img),
                )
            )
        return findings
