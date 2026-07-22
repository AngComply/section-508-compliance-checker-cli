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


# Sectioning elements. Per the HTML-ARIA mapping, a <header>/<footer> only maps
# to the banner/contentinfo landmark when it is NOT nested inside one of these.
_SECTIONING = ["article", "aside", "main", "nav", "section"]


def _is_banner(element: "Tag") -> bool:
    if _role(element) == "banner":
        return True
    if element.name == "header":
        return element.find_parent(_SECTIONING) is None
    return False


def _is_contentinfo(element: "Tag") -> bool:
    if _role(element) == "contentinfo":
        return True
    if element.name == "footer":
        return element.find_parent(_SECTIONING) is None
    return False


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


class LandmarkUniquenessCheck(Check):
    """Check that top-level banner and contentinfo landmarks are unique.

    A page has at most one banner (site ``<header>`` / ``role="banner"``) and one
    contentinfo (site ``<footer>`` / ``role="contentinfo"``). Duplicates make
    landmark navigation ambiguous for assistive-technology users. A ``<header>``
    or ``<footer>`` nested inside sectioning content (article, aside, main, nav,
    section) is not a banner/contentinfo landmark and is not counted.
    """

    id = "landmark-uniqueness"
    criterion = "1.3.1"
    criterion_name = "Info and Relationships"
    description = "Banner and contentinfo landmarks must each be unique."

    def run(self, soup: "BeautifulSoup") -> list[Finding]:
        findings: list[Finding] = []
        elements = [el for el in soup.find_all(True) if not is_hidden(el)]

        banners = [el for el in elements if _is_banner(el)]
        if len(banners) > 1:
            findings.append(
                self._finding(
                    Severity.ERROR,
                    f"The page has {len(banners)} banner landmarks; a page "
                    "should have at most one.",
                    'Keep a single top-level <header> / role="banner" and '
                    "scope the others (e.g. move them inside a section).",
                    element_snippet(banners[1]),
                )
            )

        infos = [el for el in elements if _is_contentinfo(el)]
        if len(infos) > 1:
            findings.append(
                self._finding(
                    Severity.ERROR,
                    f"The page has {len(infos)} contentinfo landmarks; a page "
                    "should have at most one.",
                    'Keep a single top-level <footer> / role="contentinfo" and '
                    "scope the others (e.g. move them inside a section).",
                    element_snippet(infos[1]),
                )
            )

        return findings
