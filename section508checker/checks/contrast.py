"""Colour-contrast check (WCAG 1.4.3 Contrast (Minimum), Level AA).

Two evaluation modes
--------------------
* **Full-page (Selenium):** when the Selenium backend supplies browser-computed
  styles, every text-bearing element is assessed using its real rendered colour
  and background, regardless of whether those come from inline styles, embedded
  or external CSS, or inheritance.
* **Inline (static):** without computed styles, only colours declared in inline
  ``style`` attributes are visible, so an element is assessed only when both its
  foreground and an opaque background are determinable inline (on the element or
  an ancestor). Indeterminate cases are skipped rather than guessed, keeping the
  check free of false positives at the cost of coverage.

Run the tool with ``--render selenium`` to get full-page coverage.
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
_WHITE = (255, 255, 255)


def required_ratio(px: float | None, bold: bool) -> float:
    """Return the WCAG AA ratio (4.5 or 3.0) for the given text metrics.

    When the size is unknown the stricter normal-text threshold is assumed.
    """
    if px is None:
        return _AA_NORMAL
    if px >= _LARGE_PX or (px >= _LARGE_BOLD_PX and bold):
        return _AA_LARGE
    return _AA_NORMAL


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
    """Flag text that falls below the WCAG AA contrast ratio.

    Uses browser-computed styles (full-page) when ``computed_styles`` is set by
    the runner; otherwise falls back to inline-style analysis.
    """

    id = "color-contrast"
    criterion = "1.4.3"
    criterion_name = "Contrast (Minimum)"
    description = (
        "Text must meet WCAG AA contrast against its background "
        "(full page under --render selenium; inline styles otherwise)."
    )

    #: Optional browser-computed style records, injected by the runner.
    computed_styles: list[dict] | None = None

    def run(self, soup: "BeautifulSoup") -> list[Finding]:
        if self.computed_styles is not None:
            return self._run_computed(self.computed_styles)
        return self._run_inline(soup)

    # -- full-page mode (Selenium computed styles) -----------------------------

    def _run_computed(self, records: list[dict]) -> list[Finding]:
        findings: list[Finding] = []
        for record in records:
            foreground = parse_color(record.get("color", ""))
            background = parse_color(record.get("background", ""))
            if foreground is None or background is None:
                continue

            bg_rgb = (
                composite_over(background, _WHITE)
                if background[3] < 1.0
                else background[:3]
            )
            fg_rgb = (
                composite_over(foreground, bg_rgb)
                if foreground[3] < 1.0
                else foreground[:3]
            )
            ratio = contrast_ratio(fg_rgb, bg_rgb)
            px = record.get("fontSize")
            bold = (record.get("fontWeight") or 400) >= 700
            needed = required_ratio(px, bold)

            if round(ratio, 2) < needed:
                snippet = " ".join(str(record.get("snippet", "")).split())[:120]
                findings.append(self._contrast_finding(ratio, bg_rgb, needed, snippet))
        return findings

    # -- inline mode (static) --------------------------------------------------

    def _run_inline(self, soup: "BeautifulSoup") -> list[Finding]:
        findings: list[Finding] = []
        for element in soup.find_all(style=True):
            styles = _parse_style(str(element.get("style") or ""))
            if "color" not in styles:
                continue
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
            needed = required_ratio(_font_px(styles), _is_bold(styles))

            if round(ratio, 2) < needed:
                findings.append(
                    self._contrast_finding(
                        ratio, background, needed, element_snippet(element)
                    )
                )
        return findings

    # -- shared helpers --------------------------------------------------------

    def _contrast_finding(
        self,
        ratio: float,
        bg_rgb: tuple[int, int, int],
        needed: float,
        snippet: str,
    ) -> Finding:
        size = "large" if needed == _AA_LARGE else "normal"
        bg_hex = "#{:02x}{:02x}{:02x}".format(*bg_rgb)
        return self._finding(
            Severity.ERROR,
            f"Text contrast ratio is {ratio:.2f}:1 against background {bg_hex}; "
            f"WCAG AA requires at least {needed:g}:1 for {size} text.",
            "Darken or lighten the text or background so the ratio "
            f"meets {needed:g}:1.",
            snippet,
        )

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
            token = _background_from_style(_parse_style(str(style)))
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
