"""Landmark and bypass-block checks (WCAG 1.3.1 Info and Relationships,
2.4.1 Bypass Blocks)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .base import Check, Finding, Severity, element_snippet
from .naming import attr_text, is_hidden

if TYPE_CHECKING:  # pragma: no cover - typing only
    from bs4 import BeautifulSoup
    from bs4.element import Tag


def _role(element: "Tag") -> str:
    return attr_text(element, "role").lower()


def _is_main(element: "Tag") -> bool:
    return element.name == "main" or _role(element) == "main"


def _is_nav(element: "Tag") -> bool:
    return element.name == "nav" or _role(element) == "navigation"


class MainLandmarkCheck(Check):
    """Check that the page exposes exactly one main landmark.

    A single ``<main>`` (or ``role="main"``) lets assistive-technology users jump
    straight to the primary content. Its absence is advisory (WCAG does not
    mandate ``<main>``); more than one is invalid and breaks landmark navigation.
    """

    id = "main-landmark"
    criterion = "1.3.1"
    criterion_name = "Info and Relationships"
    description = "The page should expose exactly one main landmark."

    def run(self, soup: "BeautifulSoup") -> list[Finding]:
        mains = [el for el in soup.find_all(True) if _is_main(el) and not is_hidden(el)]
        if not mains:
            return [
                self._finding(
                    Severity.WARNING,
                    "The page has no main landmark, so assistive-technology "
                    "users cannot jump directly to the primary content.",
                    'Wrap the primary content in a <main> element (or role="main").',
                )
            ]
        if len(mains) > 1:
            return [
                self._finding(
                    Severity.ERROR,
                    f"The page has {len(mains)} main landmarks; only one is allowed.",
                    'Keep a single <main> / role="main" and remove or relabel '
                    "the others.",
                    element_snippet(mains[1]),
                )
            ]
        return []


class SkipLinkCheck(Check):
    """Check for a skip link when the page has a navigation landmark.

    When navigation is present, a skip link lets keyboard and screen-reader
    users bypass it and reach the main content (WCAG 2.4.1). Only flagged when a
    navigation landmark exists, so pages with nothing to bypass are not warned.
    """

    id = "skip-link"
    criterion = "2.4.1"
    criterion_name = "Bypass Blocks"
    description = "Provide a skip link to bypass repeated navigation."

    def run(self, soup: "BeautifulSoup") -> list[Finding]:
        navs = [el for el in soup.find_all(True) if _is_nav(el) and not is_hidden(el)]
        if not navs:
            return []  # no navigation landmark to bypass; nothing to flag

        for anchor in soup.find_all("a", href=True):
            href = attr_text(anchor, "href")
            label = (
                anchor.get_text(strip=True) + " " + attr_text(anchor, "aria-label")
            ).lower()
            # A skip link is an in-page anchor whose name mentions skipping.
            if href.startswith("#") and len(href) > 1 and "skip" in label:
                return []

        return [
            self._finding(
                Severity.WARNING,
                "The page has navigation but no skip link to bypass it.",
                "Add a skip-to-content link as the first focusable element, "
                'e.g. <a href="#main">Skip to main content</a>.',
            )
        ]
