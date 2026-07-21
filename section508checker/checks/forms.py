"""Form-control labelling checks (WCAG 1.3.1 Info and Relationships,
4.1.2 Name, Role, Value)."""
from __future__ import annotations

from typing import TYPE_CHECKING

from .base import Check, Finding, Severity, element_snippet
from .naming import attr_text, has_aria_name, is_hidden

if TYPE_CHECKING:  # pragma: no cover - typing only
    from bs4 import BeautifulSoup
    from bs4.element import Tag

# Input types that do not take a text label (their own semantics name them, or
# they are not user-editable controls).
_UNLABELLED_INPUT_TYPES = {"hidden", "submit", "reset", "button"}


def _has_associated_label(control: "Tag", soup: "BeautifulSoup") -> bool:
    """True if the control is named by a <label> (explicit for= or wrapping)."""
    control_id = attr_text(control, "id")
    if control_id:
        for label in soup.find_all("label"):
            if attr_text(label, "for") == control_id:
                if label.get_text(strip=True) or label.find("img", alt=True):
                    return True
    # Implicit association: the control is nested inside a <label>.
    parent_label = control.find_parent("label")
    if parent_label is not None and parent_label.get_text(strip=True):
        return True
    return False


def _has_accessible_name(control: "Tag", soup: "BeautifulSoup") -> bool:
    return has_aria_name(control) or _has_associated_label(control, soup)


class FormLabelCheck(Check):
    """Flag form controls that have no programmatically associated label."""

    id = "form-label"
    criterion = "1.3.1"
    criterion_name = "Info and Relationships"
    description = "Form controls must have an associated, descriptive label."

    def run(self, soup: "BeautifulSoup") -> list[Finding]:
        findings: list[Finding] = []
        for control in soup.find_all(["input", "select", "textarea"]):
            if is_hidden(control):
                continue

            input_type = attr_text(control, "type").lower()

            if control.name == "input" and input_type in _UNLABELLED_INPUT_TYPES:
                continue

            # An image button conveys its name through alt text.
            if control.name == "input" and input_type == "image":
                if not attr_text(control, "alt") and not has_aria_name(control):
                    findings.append(
                        self._finding(
                            Severity.ERROR,
                            "Image input has no alt text or accessible name.",
                            "Add alt text describing the button's action, e.g. "
                            'alt="Search".',
                            element_snippet(control),
                        )
                    )
                continue

            if _has_accessible_name(control, soup):
                continue

            label_hint = ""
            if attr_text(control, "placeholder"):
                label_hint = (
                    " A placeholder is present but does not substitute for a "
                    "label."
                )
            findings.append(
                self._finding(
                    Severity.ERROR,
                    f"<{control.name}> control has no associated label."
                    + label_hint,
                    "Associate a <label for> element, or add aria-label / "
                    "aria-labelledby.",
                    element_snippet(control),
                )
            )
        return findings
