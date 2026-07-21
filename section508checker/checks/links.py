"""Link accessibility checks (WCAG 2.4.4 Link Purpose,
4.1.2 Name, Role, Value)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .base import Check, Finding, Severity, element_snippet
from .naming import has_aria_name, is_hidden

if TYPE_CHECKING:  # pragma: no cover - typing only
    from bs4 import BeautifulSoup
    from bs4.element import Tag

# Ambiguous phrases that give no context when a link is read out of context.
_GENERIC_LINK_TEXT = {
    "click here",
    "here",
    "read more",
    "more",
    "learn more",
    "link",
    "this",
    "this page",
    "details",
}


def _link_has_image_name(anchor: "Tag") -> bool:
    """True if the link wraps an image that supplies a non-empty accessible name."""
    for img in anchor.find_all("img"):
        alt = img.get("alt")
        if alt is not None and alt.strip():
            return True
        if has_aria_name(img):
            return True
    return False


class LinkTextCheck(Check):
    """Flag links with no discernible text, or with generic link text."""

    id = "link-text"
    criterion = "2.4.4"
    criterion_name = "Link Purpose (In Context)"
    description = "Links must have discernible, descriptive text."

    def run(self, soup: "BeautifulSoup") -> list[Finding]:
        findings: list[Finding] = []
        for anchor in soup.find_all("a"):
            # Only hyperlinks expose the "link" role; in-page anchors without
            # href are not actionable links.
            if not anchor.has_attr("href") or is_hidden(anchor):
                continue

            text = anchor.get_text(strip=True)

            if (
                not text
                and not has_aria_name(anchor)
                and not _link_has_image_name(anchor)
            ):
                findings.append(
                    self._finding(
                        Severity.ERROR,
                        "Link has no discernible text.",
                        "Add descriptive link text, or an aria-label / alt text "
                        "if the link contains only an image or icon.",
                        element_snippet(anchor),
                    )
                )
                continue

            if text and text.lower() in _GENERIC_LINK_TEXT:
                findings.append(
                    self._finding(
                        Severity.WARNING,
                        f"Link text {text!r} does not describe the link's destination.",
                        "Use text that makes sense out of context, e.g. "
                        '"Read the 2024 accessibility report".',
                        element_snippet(anchor),
                    )
                )
        return findings
