"""Non-text contrast for user-interface components (WCAG 1.4.11).

Scope
-----
This check targets **editable text fields** (``input`` text types, ``select``,
``textarea``) — the clearest, lowest-ambiguity 1.4.11 case. A field's visual
boundary must reach 3:1 contrast against the surrounding background so users can
perceive where the control is. It is flagged only when the boundary is
imperceptible by *any* means: no box-shadow, and neither the border nor the
control's own fill reaches 3:1 against the surroundings. Buttons, checkboxes,
and radios are intentionally excluded (frequently borderless by design and prone
to false positives).

Like the text-contrast check, it runs full-page from Selenium computed styles
(``--render selenium``) and falls back to inline styles otherwise; when the
surrounding background cannot be resolved, the control is skipped rather than
guessed.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .base import Check, Finding, Severity, element_snippet
from .color import RGBA, composite_over, contrast_ratio, parse_color

if TYPE_CHECKING:  # pragma: no cover - typing only
    from bs4 import BeautifulSoup
    from bs4.element import Tag

_MIN_RATIO = 3.0
_VISIBLE_BORDER_STYLES = {
    "solid",
    "dashed",
    "dotted",
    "double",
    "groove",
    "ridge",
    "inset",
    "outset",
}
# Editable text field input types assessed by this check.
_TEXT_INPUT_TYPES = {
    "",
    "text",
    "email",
    "password",
    "search",
    "tel",
    "url",
    "number",
    "date",
    "datetime-local",
    "month",
    "week",
    "time",
}


def _solid(color: RGBA | None, over: tuple[int, int, int]) -> tuple[int, int, int]:
    """Flatten a possibly-translucent colour onto an opaque background."""
    if color is None:
        return over
    if color[3] <= 0:
        return over
    if color[3] < 1.0:
        return composite_over(color, over)
    return color[:3]


def _boundary_ratio(
    border: RGBA | None,
    border_visible: bool,
    fill: tuple[int, int, int],
    surround: tuple[int, int, int],
    has_shadow: bool,
) -> float | None:
    """Best contrast the control boundary achieves, or None if perceivable
    by a means we do not score (a box-shadow).

    The boundary is perceivable when the border contrasts with an adjacent
    surface, or when the fill contrasts with the surrounding background.
    """
    if has_shadow:
        return None  # a shadow delineates the control; do not flag
    ratios = [contrast_ratio(fill, surround)]
    if border_visible and border is not None:
        border_rgb_out = _solid(border, surround)
        border_rgb_in = _solid(border, fill)
        ratios.append(contrast_ratio(border_rgb_out, surround))
        ratios.append(contrast_ratio(border_rgb_in, fill))
    return max(ratios)


# --------------------------------------------------------------------------
# Inline-style parsing (static mode)
# --------------------------------------------------------------------------


def _parse_style(style: str) -> dict[str, str]:
    declarations: dict[str, str] = {}
    for part in style.split(";"):
        if ":" not in part:
            continue
        name, _, value = part.partition(":")
        value = value.replace("!important", "").strip()
        if name.strip() and value:
            declarations[name.strip().lower()] = value
    return declarations


def _parse_border(styles: dict[str, str]) -> tuple[RGBA | None, bool]:
    """Return (border colour, is-visible) from inline border declarations."""
    style = styles.get("border-style", "")
    width = styles.get("border-width", "")
    color = styles.get("border-color", "")

    # The `border` shorthand can supply any of the three.
    if "border" in styles:
        for token in styles["border"].split():
            if token in _VISIBLE_BORDER_STYLES or token in {"none", "hidden"}:
                style = style or token
            elif (
                token.endswith(("px", "em", "rem"))
                or token.replace(".", "", 1).isdigit()
            ):
                width = width or token
            elif parse_color(token) is not None:
                color = color or token

    visible = style in _VISIBLE_BORDER_STYLES and not _is_zero_width(width)
    return parse_color(color), visible


def _is_zero_width(width: str) -> bool:
    width = width.strip()
    if not width:
        return False  # unspecified width with a style still paints (medium)
    number = width.rstrip("pxemr").strip()
    try:
        return float(number) == 0
    except ValueError:
        return False


def _resolve_inline_bg(element: "Tag") -> tuple[int, int, int] | None:
    """Nearest opaque inline background from ``element`` upward, or None."""
    layers: list[RGBA] = []
    for node in [element, *element.parents]:
        if not getattr(node, "get", None):
            continue
        style = node.get("style")
        if not style:
            continue
        styles = _parse_style(str(style))
        if "background-image" in styles and styles["background-image"] != "none":
            return None
        token = styles.get("background-color") or _color_from_background(styles)
        color = parse_color(token) if token else None
        if color is None or color[3] <= 0:
            continue
        layers.append(color)
        if color[3] >= 1.0:
            rgb = color[:3]
            for lower in reversed(layers[:-1]):
                rgb = composite_over(lower, rgb)
            return rgb
    return None


def _color_from_background(styles: dict[str, str]) -> str | None:
    if "background" not in styles:
        return None
    for token in styles["background"].split():
        if parse_color(token) is not None:
            return token
    return None


class NonTextContrastCheck(Check):
    """Flag editable text fields whose boundary is below WCAG AA (1.4.11)."""

    id = "nontext-contrast"
    criterion = "1.4.11"
    criterion_name = "Non-text Contrast"
    description = (
        "Form-field boundaries must meet 3:1 contrast against their surroundings "
        "(full page under --render selenium; inline styles otherwise)."
    )

    #: Optional browser-computed component records, injected by the runner.
    component_styles: list[dict] | None = None

    def run(self, soup: "BeautifulSoup") -> list[Finding]:
        if self.component_styles is not None:
            return self._run_computed(self.component_styles)
        return self._run_inline(soup)

    def _emit(self, ratio: float, snippet: str) -> Finding:
        # Reported as a warning: the ratio is measured precisely, but a
        # definitive 1.4.11 determination for a form field also depends on
        # context (visible label, user-agent styling), so it warrants review.
        return self._finding(
            Severity.WARNING,
            f"Form field boundary contrast is {ratio:.2f}:1 against its "
            "surroundings, below the WCAG 1.4.11 minimum of 3:1; verify the "
            "field's edges remain perceivable.",
            "Strengthen the field's border or fill so it reaches 3:1 against "
            "the adjacent background.",
            snippet,
        )

    def _run_computed(self, records: list[dict]) -> list[Finding]:
        findings: list[Finding] = []
        for record in records:
            surround_color = parse_color(record.get("surround") or "")
            if surround_color is None:
                continue  # indeterminate surrounding background: skip
            surround = surround_color[:3]

            fill = _solid(parse_color(record.get("background") or ""), surround)
            border = parse_color(record.get("borderColor") or "")
            border_visible = (
                record.get("borderStyle")
                not in (
                    None,
                    "none",
                    "hidden",
                )
                and (record.get("borderWidth") or 0) > 0
            )
            box_shadow = record.get("boxShadow") or "none"
            has_shadow = box_shadow != "none"

            ratio = _boundary_ratio(border, border_visible, fill, surround, has_shadow)
            if ratio is not None and round(ratio, 2) < _MIN_RATIO:
                snippet = " ".join(str(record.get("snippet", "")).split())[:120]
                findings.append(self._emit(ratio, snippet))
        return findings

    def _run_inline(self, soup: "BeautifulSoup") -> list[Finding]:
        findings: list[Finding] = []
        for control in soup.find_all(["input", "select", "textarea"]):
            if control.name == "input":
                input_type = str(control.get("type") or "").strip().lower()
                if input_type not in _TEXT_INPUT_TYPES:
                    continue

            # The surrounding background is what sits *behind* the control, so
            # resolve it from the parent upward (not the control's own fill).
            parent = control.parent
            surround = _resolve_inline_bg(parent) if parent is not None else None
            if surround is None:
                continue

            styles = _parse_style(str(control.get("style") or ""))
            fill_token = styles.get("background-color") or _color_from_background(
                styles
            )
            fill = _solid(parse_color(fill_token) if fill_token else None, surround)
            border, border_visible = _parse_border(styles)
            has_shadow = bool(styles.get("box-shadow"))

            ratio = _boundary_ratio(border, border_visible, fill, surround, has_shadow)
            if ratio is not None and round(ratio, 2) < _MIN_RATIO:
                findings.append(self._emit(ratio, element_snippet(control)))
        return findings
