"""Accessibility check registry.

``CHECKS`` is the ordered list of check classes the CLI runs. To add a new
check, implement a :class:`~section508checker.checks.base.Check` subclass and
append it here.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .base import Check, Finding, Severity
from .document import DocumentLanguageCheck, PageTitleCheck
from .forms import FormLabelCheck
from .frames import FrameTitleCheck
from .headings import HeadingStructureCheck
from .images import ImageAltTextCheck
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
]


def run_all(soup: "BeautifulSoup") -> tuple[list[Finding], int, int]:
    """Run every registered check against ``soup``.

    Returns a tuple of ``(findings, checks_run, checks_passed)`` where a check
    "passes" when it produces no findings.
    """
    findings: list[Finding] = []
    passed = 0
    for check_cls in CHECKS:
        result = check_cls().run(soup)
        if result:
            findings.extend(result)
        else:
            passed += 1
    return findings, len(CHECKS), passed


__all__ = ["CHECKS", "Check", "Finding", "Severity", "run_all"]
