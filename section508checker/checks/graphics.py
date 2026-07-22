"""Non-text contrast for meaningful graphics (WCAG 1.4.11).

Consumes the graphic records collected by the Selenium backend — only SVGs that
expose an accessible name or ``role="img"`` (decorative icons are exempt and
already filtered out). A graphic is flagged when its fill (or, failing that,
stroke) colour is below 3:1 against its background. Backgrounds that could not
be resolved from the DOM are pixel-sampled by the loader, so gradient/overlay
cases are handled; genuinely unresolvable ones are skipped.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .base import Check, Finding, Severity
from .color import composite_over, contrast_ratio, parse_color

if TYPE_CHECKING:  # pragma: no cover - typing only
    from bs4 import BeautifulSoup

_MIN_RATIO = 3.0
_WHITE = (255, 255, 255)


def _icon_color(graphic: dict):
    """Representative colour of the graphic: fill, else stroke."""
    for key in ("fill", "stroke"):
        color = parse_color(str(graphic.get(key) or ""))
        if color is not None and color[3] > 0:
            return color
    return None


class IconContrastCheck(Check):
    """Flag meaningful graphics whose contrast is below WCAG AA (1.4.11)."""

    id = "icon-contrast"
    criterion = "1.4.11"
    criterion_name = "Non-text Contrast"
    description = "Meaningful graphics must meet 3:1 contrast against their background."

    #: Graphic records injected by the runner (Selenium backend only).
    graphic_styles: list[dict] | None = None

    def run(self, soup: "BeautifulSoup") -> list[Finding]:
        if self.graphic_styles is None:
            return []
        findings: list[Finding] = []
        for graphic in self.graphic_styles:
            background = parse_color(str(graphic.get("background") or ""))
            color = _icon_color(graphic)
            if background is None or color is None:
                continue

            bg_rgb = (
                composite_over(background, _WHITE)
                if background[3] < 1.0
                else background[:3]
            )
            fg_rgb = composite_over(color, bg_rgb) if color[3] < 1.0 else color[:3]
            ratio = contrast_ratio(fg_rgb, bg_rgb)

            if round(ratio, 2) < _MIN_RATIO:
                snippet = " ".join(str(graphic.get("snippet", ""))[:120].split())
                findings.append(
                    self._finding(
                        Severity.WARNING,
                        f"Graphic contrast is {ratio:.2f}:1 against its "
                        "background, below the WCAG 1.4.11 minimum of 3:1 for "
                        "meaningful graphics.",
                        "Increase the icon/graphic colour contrast against its "
                        "background to at least 3:1.",
                        snippet,
                    )
                )
        return findings
