"""Shared heuristics for accessible names and hidden elements.

These are deliberately conservative approximations of the WAI-ARIA accessible
name computation. They cannot fully resolve ``aria-labelledby`` references or
CSS-driven hiding from static markup, so they err toward *not* raising false
positives when an ARIA hook is present.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - typing only
    from bs4.element import Tag

# Roles that expose an element as decorative / removed from the accessibility tree.
_PRESENTATION_ROLES = {"presentation", "none"}


def attr_text(tag: "Tag", name: str) -> str:
    """Return a stripped attribute value, or ``""`` if absent/blank."""
    value = tag.get(name)
    if value is None:
        return ""
    # BeautifulSoup returns a list for space-separated attrs like class; guard it.
    if isinstance(value, list):
        value = " ".join(value)
    return value.strip()


def is_hidden(tag: "Tag") -> bool:
    """True if the element is explicitly hidden from assistive technology.

    Detects ``aria-hidden="true"``, the boolean ``hidden`` attribute, and the
    presentational roles. CSS-based hiding is not detectable from static markup.
    """
    if attr_text(tag, "aria-hidden").lower() == "true":
        return True
    if tag.has_attr("hidden"):
        return True
    if attr_text(tag, "role").lower() in _PRESENTATION_ROLES:
        return True
    return False


def has_aria_name(tag: "Tag") -> bool:
    """True if the element carries an explicit ARIA/title accessible name hook."""
    return bool(
        attr_text(tag, "aria-label")
        or attr_text(tag, "aria-labelledby")
        or attr_text(tag, "title")
    )
