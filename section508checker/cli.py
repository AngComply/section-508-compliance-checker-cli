"""Argument parsing and orchestration for the Section 508 Compliance Checker."""

from __future__ import annotations

import argparse
import os
import sys

from . import __version__
from .checks import run_all
from .loader import DEFAULT_TIMEOUT, LoaderError, load_html
from .report import Report, render

# Process exit codes.
EXIT_OK = 0  # ran successfully; no failure threshold met
EXIT_FINDINGS = 1  # ran successfully; findings met the --fail-on threshold
EXIT_ERROR = 2  # could not run (bad usage, load/parse failure)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="checker.py",
        description=(
            "Detect common Section 508 / WCAG accessibility barriers in web "
            "content. Automated checks complement — they do not replace — "
            "manual testing with assistive technology."
        ),
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )

    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--url", help="URL of the page to scan.")
    source.add_argument("--file", help="Path to a local HTML file to scan.")

    parser.add_argument(
        "--render",
        choices=["static", "selenium"],
        default="static",
        help="Rendering backend for URLs (default: static). Use 'selenium' "
        "for JavaScript-rendered pages.",
    )
    parser.add_argument(
        "--format",
        choices=["console", "json", "markdown"],
        default="console",
        help="Report output format (default: console).",
    )
    parser.add_argument(
        "--output",
        help="Write the report to this file instead of standard output.",
    )
    parser.add_argument(
        "--fail-on",
        choices=["error", "any", "none"],
        default="error",
        help="Exit non-zero when findings are present: 'error' (default) fails "
        "only on errors, 'any' fails on any finding, 'none' never fails.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT,
        help=f"Network timeout in seconds for URL fetches (default: "
        f"{DEFAULT_TIMEOUT}).",
    )
    return parser


def _should_fail(report: Report, fail_on: str) -> bool:
    if fail_on == "none":
        return False
    if fail_on == "any":
        return bool(report.findings)
    return report.error_count > 0  # fail_on == "error"


def _use_color(args: argparse.Namespace) -> bool:
    """Enable ANSI colour only for interactive console output to a TTY."""
    if args.format != "console" or args.output:
        return False
    if os.environ.get("NO_COLOR") is not None:
        return False
    return sys.stdout.isatty()


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        from bs4 import BeautifulSoup
    except ImportError:
        print(
            "Error: the 'beautifulsoup4' package is required. Install "
            "dependencies with 'pip install -r requirements.txt'.",
            file=sys.stderr,
        )
        return EXIT_ERROR

    try:
        page = load_html(
            url=args.url,
            file=args.file,
            render=args.render,
            timeout=args.timeout,
        )
    except LoaderError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return EXIT_ERROR

    soup = BeautifulSoup(page.html, "html.parser")
    findings, checks_run, checks_passed = run_all(
        soup,
        computed_styles=page.computed_styles,
        component_styles=page.component_styles,
        graphic_styles=page.graphic_styles,
        focus_states=page.focus_states,
    )
    report = Report(
        target=args.url or args.file,
        findings=findings,
        checks_run=checks_run,
        checks_passed=checks_passed,
    )

    output = render(report, args.format, use_color=_use_color(args))

    if args.output:
        try:
            with open(args.output, "w", encoding="utf-8") as handle:
                handle.write(output + "\n")
        except OSError as exc:
            print(
                f"Error: could not write report to {args.output}: {exc}",
                file=sys.stderr,
            )
            return EXIT_ERROR
        print(f"Report written to {args.output}", file=sys.stderr)
    else:
        print(output)

    return EXIT_FINDINGS if _should_fail(report, args.fail_on) else EXIT_OK
