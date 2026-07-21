"""Data-table header checks (WCAG 1.3.1 Info and Relationships)."""
from __future__ import annotations

from typing import TYPE_CHECKING

from .base import Check, Finding, Severity, element_snippet
from .naming import attr_text, is_hidden

if TYPE_CHECKING:  # pragma: no cover - typing only
    from bs4 import BeautifulSoup


class TableHeaderCheck(Check):
    """Flag data tables that expose no header cells.

    Tables explicitly marked as presentational (``role="presentation"`` /
    ``role="none"``) are treated as layout tables and skipped. A table that
    holds data cells (``<td>``) but no header cells (``<th>``) cannot convey
    row/column relationships to assistive technology.
    """

    id = "table-headers"
    criterion = "1.3.1"
    criterion_name = "Info and Relationships"
    description = "Data tables must identify header cells with <th>."

    def run(self, soup: "BeautifulSoup") -> list[Finding]:
        findings: list[Finding] = []
        for table in soup.find_all("table"):
            if is_hidden(table):
                continue
            if attr_text(table, "role").lower() in {"presentation", "none"}:
                continue
            if table.find("th") is not None:
                continue  # has header cells
            if table.find("td") is None:
                continue  # empty / no data cells to associate
            findings.append(
                self._finding(
                    Severity.WARNING,
                    "Data table has no header cells (<th>), so row and column "
                    "relationships are not conveyed.",
                    "Mark header cells with <th> and set scope=\"col\"/\"row\". "
                    'If the table is purely for layout, add role="presentation".',
                    element_snippet(table),
                )
            )
        return findings
