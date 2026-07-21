"""Accessibility check registry.

``CHECKS`` is the ordered list of check classes the CLI runs. To add a new
check, implement a :class:`~section508checker.checks.base.Check` subclass and
append it here.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .base import Check, Finding, Severity
from .contrast import ColorContrastCheck
from .document import DocumentLanguageCheck, PageTitleCheck
from .forms import FormLabelCheck
from .frames import FrameTitleCheck
from .headings import HeadingStructureCheck
from .images import ImageAltTextCheck
from .landmarks import MainLandmarkCheck, SkipLinkCheck
from .links import LinkTextCheck
from .tables import TableHeaderCheck

if TYPE_CHECKING:  # pragma: no cover - typing only
    from bs4 import BeautifulSoup

#: Ordered registry of every check the tool runs.
CHECKS: list[type[Check]] = [
    DocumentLanguageCheck,
    PageTitleCheck,
    ImageAltTextCheck,
    FormLabelCheck,
    HeadingStructureCheck,
    LinkTextCheck,
    TableHeaderCheck,
    FrameTitleCheck,
    MainLandmarkCheck,
    SkipLinkCheck,
    ColorContrastCheck,
]


def run_all(
    soup: "BeautifulSoup",
    computed_styles: list[dict] | None = None,
) -> tuple[list[Finding], int, int]:
    """Run every registered check against ``soup``.

    When ``computed_styles`` is provided (from the Selenium backend), the
    colour-contrast check evaluates the full page rather than inline styles only.

    Returns a tuple of ``(findings, checks_run, checks_passed)`` where a check
    "passes" when it produces no findings.
    """
    findings: list[Finding] = []
    passed = 0
    for check_cls in CHECKS:
        check = check_cls()
        # The contrast check can use browser-computed styles when available.
        if isinstance(check, ColorContrastCheck):
            check.computed_styles = computed_styles
        result = check.run(soup)
        if result:
            findings.extend(result)
        else:
            passed += 1
    # Collapse byte-identical findings (e.g. a repeated component fails the same
    # way in several places); identical entries carry no extra information.
    findings = list(dict.fromkeys(findings))
    return findings, len(CHECKS), passed


__all__ = ["CHECKS", "Check", "Finding", "Severity", "run_all"]
