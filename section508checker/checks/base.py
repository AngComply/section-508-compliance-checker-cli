"""Core primitives shared by every accessibility check.

A :class:`Check` inspects a parsed HTML document and returns zero or more
:class:`Finding` objects. Each finding is tied to a specific WCAG success
criterion so results map cleanly onto Section 508 / VPAT reporting.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - typing only
    from bs4 import BeautifulSoup
    from bs4.element import Tag


class Severity(Enum):
    """Severity of a finding, ordered most- to least-critical for reporting."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"

    @property
    def rank(self) -> int:
        """Sort key: lower ranks are more severe (ERROR first)."""
        return {"error": 0, "warning": 1, "info": 2}[self.value]


@dataclass(frozen=True)
class Finding:
    """A single detected accessibility issue.

    Attributes:
        check_id: Stable identifier of the check that produced the finding.
        criterion: WCAG success-criterion number, e.g. ``"1.1.1"``.
        criterion_name: Human-readable name of the success criterion.
        severity: :class:`Severity` of the issue.
        message: What is wrong, in plain language.
        remediation: How to fix it.
        snippet: A short excerpt of the offending markup (may be empty).
    """

    check_id: str
    criterion: str
    criterion_name: str
    severity: Severity
    message: str
    remediation: str
    snippet: str = ""

    def to_dict(self) -> dict:
        """Serialise to a plain dict with a JSON-friendly severity value."""
        data = asdict(self)
        data["severity"] = self.severity.value
        return data


class Check(ABC):
    """Base class for all accessibility checks.

    Subclasses set the class attributes below and implement :meth:`run`.
    """

    #: Stable, kebab-case identifier for the check.
    id: str = ""
    #: WCAG success-criterion number this check maps to.
    criterion: str = ""
    #: Human-readable name of the success criterion.
    criterion_name: str = ""
    #: One-line description of what the check verifies.
    description: str = ""

    @abstractmethod
    def run(self, soup: "BeautifulSoup") -> list[Finding]:
        """Inspect ``soup`` and return a list of findings (empty if none)."""
        raise NotImplementedError

    def _finding(
        self,
        severity: Severity,
        message: str,
        remediation: str,
        snippet: str = "",
    ) -> Finding:
        """Construct a :class:`Finding` pre-filled with this check's metadata."""
        return Finding(
            check_id=self.id,
            criterion=self.criterion,
            criterion_name=self.criterion_name,
            severity=severity,
            message=message,
            remediation=remediation,
            snippet=snippet,
        )


def element_snippet(tag: "Tag", max_len: int = 120) -> str:
    """Return a single-line, length-capped HTML excerpt for a tag.

    The opening tag alone is used (child content is omitted) so snippets stay
    short and point precisely at the offending element.
    """
    markup = " ".join(str(tag).split())  # collapse whitespace/newlines
    # Prefer just the opening tag when the element has children.
    open_tag = markup.split(">", 1)[0] + ">" if ">" in markup else markup
    snippet = open_tag if tag.contents else markup
    if len(snippet) > max_len:
        snippet = snippet[: max_len - 1].rstrip() + "…"
    return snippet
