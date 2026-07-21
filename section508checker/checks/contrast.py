"""Colour-contrast check (WCAG 1.4.3 Contrast (Minimum), Level AA).

Scope and limitations
----------------------
This check works on *static* markup, so it can only evaluate colours declared
in inline ``style`` attributes. Colours applied via external or embedded CSS,
inheritance, or ``currentColor`` are not visible without a rendering engine, so
a text element is only assessed when **both** its foreground colour and an
opaque background colour are determinable from inline styles (on the element
itself or an ancestor). Anything indeterminate is skipped rather than guessed,
which keeps the check free of false positives at the cost of coverage. Full-page
contrast evaluation is a planned enhancement built on the Selenium backend's
computed styles.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .base import Check, Finding, Severity, element_snippet
from .color import composite_over, contrast_ratio, parse_color

if TYPE_CHECKING:  # pragma: no cover - typing only
    from bs4 import BeautifulSoup
    from bs4.element import Tag

# WCAG 2.x AA thresholds.
_AA_NORMAL = 4.5
_AA_LARGE = 3.0
# "Large text" is >= 18pt (24px) normal, or >= 14pt (18.66px) bold.
_LARGE_PX = 24.0
_LARGE_BOLD_PX = 18.66
_PT_TO_PX = 96.0 / 72.0


def _parse_style(style: str) -> dict[str, str]:
    """Parse an inline style attribute into a ``property -> value`` dict."""
    declarations: dict[str, str] = {}
    for part in style.split(";"):
        if ":" not in part:
            continue
        name, _, value = part.partition(":")
        value = value.replace("!important", "").strip()
        if name.strip() and value:
            declarations[name.strip().lower()] = value
    return declarations


def _background_from_style(styles: dict[str, str]) -> str | None:
    """Return an inline background colour token, if one is present."""
    if "background-color" in styles:
        return styles["background-color"]
    # The `background` shorthand may carry a colour among other tokens.
    if "background" in styles:
        for token in styles["background"].split():
            if parse_color(token) is not None:
                return token
    return None


def _font_px(styles: dict[str, str]) -> float | None:
    """Parse an inline font-size to pixels (px and pt units supported)."""
    raw = styles.get("font-size")
    if not raw:
        return None
    raw = raw.strip().lower()
    try:
        if raw.endswith("px"):
            return float(raw[:-2])
        if raw.endswith("pt"):
            return float(raw[:-2]) * _PT_TO_PX
    except ValueError:
        return None
    return None


def _is_bold(styles: dict[str, str]) -> bool:
    weight = styles.get("font-weight", "").strip().lower()
    if weight in {"bold", "bolder"}:
        return True
    try:
        return int(weight) >= 700
    except ValueError:
        return False


class ColorContrastCheck(Check):
    """Flag text whose inline colours fall below the WCAG AA contrast ratio."""

    id = "color-contrast"
    criterion = "1.4.3"
    criterion_name = "Contrast (Minimum)"
    description = (
        "Text must meet WCAG AA contrast against its background "
        "(evaluated for inline-styled elements only)."
    )

    def run(self, soup: "BeautifulSoup") -> list[Finding]:
        findings: list[Finding] = []
        for element in soup.find_all(style=True):
            styles = _parse_style(element.get("style", ""))
            if "color" not in styles:
                continue
            # Only assess elements that actually render text.
            if not element.get_text(strip=True):
                continue

            foreground = parse_color(styles["color"])
            if foreground is None:
                continue

            background = self._resolve_background(element)
            if background is None:
                continue

            fg_rgb = (
                composite_over(foreground, background)
                if foreground[3] < 1.0
                else foreground[:3]
            )
            ratio = contrast_ratio(fg_rgb, background)
            required = self._required_ratio(styles)

            if round(ratio, 2) < required:
                size = "large" if required == _AA_LARGE else "normal"
                bg_hex = "#{:02x}{:02x}{:02x}".format(*background)
                findings.append(
                    self._finding(
                        Severity.ERROR,
                        f"Text contrast ratio is {ratio:.2f}:1 against "
                        f"background {bg_hex}; WCAG AA requires at least "
                        f"{required:g}:1 for {size} text.",
                        "Darken or lighten the text or background so the ratio "
                        f"meets {required:g}:1.",
                        element_snippet(element),
                    )
                )
        return findings

    def _resolve_background(self, element: "Tag") -> tuple[int, int, int] | None:
        """Find the nearest determinable, opaque inline background colour.

        Walks the element and its ancestors. Returns None if the nearest
        specified background is translucent (the colour behind it is unknown)
        or if no background is specified anywhere up the tree.
        """
        for node in [element, *element.parents]:
            if not getattr(node, "get", None):
                continue
            style = node.get("style")
            if not style:
                continue
            token = _background_from_style(_parse_style(style))
            if token is None:
                continue
            color = parse_color(token)
            if color is None:
                continue
            if color[3] < 1.0:
                # Translucent background: what is behind it is unknown.
                return None
            return color[:3]
        return None

    def _required_ratio(self, styles: dict[str, str]) -> float:
        px = _font_px(styles)
        if px is None:
            return _AA_NORMAL  # size unknown: assume the stricter threshold
        if px >= _LARGE_PX or (px >= _LARGE_BOLD_PX and _is_bold(styles)):
            return _AA_LARGE
        return _AA_NORMAL
