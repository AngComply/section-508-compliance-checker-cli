"""Report assembly and rendering (console, JSON, Markdown)."""
from __future__ import annotations

import json
from dataclasses import dataclass, field

from .checks.base import Finding, Severity

# ANSI colour codes keyed by severity, used only for TTY console output.
_COLORS = {
    Severity.ERROR: "\033[31m",  # red
    Severity.WARNING: "\033[33m",  # yellow
    Severity.INFO: "\033[36m",  # cyan
}
_BOLD = "\033[1m"
_DIM = "\033[2m"
_RESET = "\033[0m"


@dataclass
class Report:
    """The full result of a scan, ready to be rendered in any format."""

    target: str
    findings: list[Finding] = field(default_factory=list)
    checks_run: int = 0
    checks_passed: int = 0

    @property
    def error_count(self) -> int:
        return sum(f.severity is Severity.ERROR for f in self.findings)

    @property
    def warning_count(self) -> int:
        return sum(f.severity is Severity.WARNING for f in self.findings)

    @property
    def info_count(self) -> int:
        return sum(f.severity is Severity.INFO for f in self.findings)

    def sorted_findings(self) -> list[Finding]:
        """Findings ordered most-severe first, preserving discovery order."""
        return sorted(self.findings, key=lambda f: f.severity.rank)


def render(report: Report, fmt: str, use_color: bool = False) -> str:
    """Render ``report`` in the requested format ('console', 'json', 'markdown')."""
    if fmt == "json":
        return _render_json(report)
    if fmt == "markdown":
        return _render_markdown(report)
    if fmt == "console":
        return _render_console(report, use_color)
    raise ValueError(f"Unknown report format: {fmt!r}")


def _plural(count: int, noun: str) -> str:
    return f"{count} {noun}" + ("" if count == 1 else "s")


def _summary_line(report: Report) -> str:
    return (
        f"{_plural(report.error_count, 'error')}, "
        f"{_plural(report.warning_count, 'warning')}, "
        f"{report.checks_passed} of {report.checks_run} checks passed"
    )


def _render_console(report: Report, use_color: bool) -> str:
    def paint(text: str, code: str) -> str:
        return f"{code}{text}{_RESET}" if use_color else text

    lines = [
        paint(f"Section 508 Compliance Report — {report.target}", _BOLD),
        "=" * 60,
    ]

    if not report.findings:
        lines.append("No automated issues detected.")
    else:
        for finding in report.sorted_findings():
            tag = f"[{finding.severity.name}]"
            header = (
                f"{paint(tag, _COLORS[finding.severity])}  "
                f"{finding.criterion}  {finding.criterion_name}"
            )
            lines.append(header)
            lines.append(f"        {finding.message}")
            if finding.snippet:
                lines.append(paint(f"        {finding.snippet}", _DIM))
            lines.append(f"        → {finding.remediation}")
            lines.append("")

    lines.append("-" * 60)
    lines.append(f"Summary: {_summary_line(report)}")
    lines.append(
        paint(
            "Note: automated checks are not a substitute for manual testing "
            "with assistive technology.",
            _DIM,
        )
    )
    return "\n".join(lines)


def _render_json(report: Report) -> str:
    payload = {
        "target": report.target,
        "summary": {
            "errors": report.error_count,
            "warnings": report.warning_count,
            "infos": report.info_count,
            "checks_run": report.checks_run,
            "checks_passed": report.checks_passed,
        },
        "findings": [f.to_dict() for f in report.sorted_findings()],
        "disclaimer": (
            "Automated checks detect a subset of accessibility issues and do "
            "not certify Section 508 compliance. Manual testing with assistive "
            "technology is required for a conformance determination."
        ),
    }
    return json.dumps(payload, indent=2)


def _md_cell(text: str) -> str:
    """Escape prose for a Markdown table cell.

    Angle brackets are converted to entities so element names written inline
    (e.g. ``<html>``) render literally instead of being parsed as HTML tags and
    dropped. Pipes are escaped so they do not break the table column, and
    newlines are flattened.
    """
    return (
        text.replace("|", "\\|")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("\n", " ")
    )


def _md_code(text: str) -> str:
    """Format an element snippet as a table-safe inline code span.

    Inside a code span angle brackets are already literal, so only the pipe
    (which would otherwise split the table cell) needs escaping.
    """
    if not text:
        return ""
    return "`" + text.replace("|", "\\|").replace("\n", " ") + "`"


def _render_markdown(report: Report) -> str:
    lines = [
        "# Section 508 Compliance Report",
        "",
        f"**Target:** {report.target}",
        "",
        f"**Summary:** {_summary_line(report)}",
        "",
    ]

    if not report.findings:
        lines.append("No automated issues detected.")
    else:
        lines.append("| Severity | Criterion | Issue | Element | Remediation |")
        lines.append("| --- | --- | --- | --- | --- |")
        for finding in report.sorted_findings():
            criterion = f"{finding.criterion} {finding.criterion_name}"
            lines.append(
                f"| {finding.severity.name} "
                f"| {_md_cell(criterion)} "
                f"| {_md_cell(finding.message)} "
                f"| {_md_code(finding.snippet)} "
                f"| {_md_cell(finding.remediation)} |"
            )

    lines.extend(
        [
            "",
            "---",
            "",
            "> Automated checks detect a subset of accessibility issues and do "
            "not certify Section 508 compliance. Manual testing with assistive "
            "technology is required for a conformance determination.",
        ]
    )
    return "\n".join(lines)
