"""Document-level checks: language (WCAG 3.1.1) and page title (WCAG 2.4.2)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .base import Check, Finding, Severity, element_snippet

if TYPE_CHECKING:  # pragma: no cover - typing only
    from bs4 import BeautifulSoup

# Titles that are technically present but convey no information about the page.
_GENERIC_TITLES = {
    "",
    "home",
    "untitled",
    "untitled document",
    "untitled page",
    "document",
    "page",
    "new page",
    "index",
    "default",
}


class DocumentLanguageCheck(Check):
    """Flag a missing or empty ``lang`` attribute on the ``<html>`` element."""

    id = "html-lang"
    criterion = "3.1.1"
    criterion_name = "Language of Page"
    description = "The <html> element must declare the page's default language."

    def run(self, soup: "BeautifulSoup") -> list[Finding]:
        html = soup.find("html")
        if html is None:
            return [
                self._finding(
                    Severity.ERROR,
                    "No <html> element was found, so the page language cannot "
                    "be determined.",
                    'Wrap the document in <html lang="…"> declaring its '
                    "primary language.",
                )
            ]
        lang = (html.get("lang") or "").strip()
        if not lang:
            return [
                self._finding(
                    Severity.ERROR,
                    "The <html> element is missing a valid lang attribute.",
                    'Add a language code, e.g. <html lang="en">.',
                    element_snippet(html),
                )
            ]
        return []


class PageTitleCheck(Check):
    """Flag a missing, empty, or non-descriptive ``<title>``."""

    id = "page-title"
    criterion = "2.4.2"
    criterion_name = "Page Titled"
    description = "The document must have a unique, descriptive <title>."

    def run(self, soup: "BeautifulSoup") -> list[Finding]:
        title = soup.find("title")
        if title is None or not title.get_text(strip=True):
            return [
                self._finding(
                    Severity.ERROR,
                    "The document has no <title> or the title is empty.",
                    "Add a unique <title> that describes the page's topic or purpose.",
                )
            ]
        text = title.get_text(strip=True)
        if text.lower() in _GENERIC_TITLES:
            return [
                self._finding(
                    Severity.WARNING,
                    f"The page title {text!r} is generic and non-descriptive.",
                    "Use a specific title that distinguishes this page from "
                    "others on the site.",
                    element_snippet(title),
                )
            ]
        return []
