"""End-to-end tests driving the CLI through section508checker.cli.main."""

from __future__ import annotations

import json
import pathlib

from section508checker.cli import EXIT_FINDINGS, EXIT_OK, main

FIXTURE = str(pathlib.Path(__file__).parent / "fixtures" / "sample_inaccessible.html")


def test_console_run_reports_findings_and_fails_on_error(capsys):
    exit_code = main(["--file", FIXTURE, "--format", "console"])
    out = capsys.readouterr().out
    assert exit_code == EXIT_FINDINGS  # default --fail-on=error, errors present
    assert "Section 508 Compliance Report" in out
    assert "[ERROR]" in out
    assert "Summary:" in out


def test_fail_on_none_returns_ok(capsys):
    exit_code = main(["--file", FIXTURE, "--fail-on", "none"])
    capsys.readouterr()
    assert exit_code == EXIT_OK


def test_json_output_is_valid_and_structured(capsys):
    exit_code = main(["--file", FIXTURE, "--format", "json"])
    out = capsys.readouterr().out
    assert exit_code == EXIT_FINDINGS
    payload = json.loads(out)
    assert payload["target"] == FIXTURE
    assert payload["summary"]["checks_run"] == 16
    assert payload["summary"]["errors"] >= 1
    assert isinstance(payload["findings"], list)
    assert payload["findings"][0]["severity"] == "error"  # sorted, errors first


def test_markdown_output_written_to_file(tmp_path, capsys):
    out_file = tmp_path / "report.md"
    exit_code = main(
        [
            "--file",
            FIXTURE,
            "--format",
            "markdown",
            "--output",
            str(out_file),
        ]
    )
    assert exit_code == EXIT_FINDINGS
    content = out_file.read_text(encoding="utf-8")
    assert content.startswith("# Section 508 Compliance Report")
    assert "| Severity | Criterion |" in content
    # Confirmation goes to stderr, not stdout.
    assert "Report written to" in capsys.readouterr().err


def test_clean_document_passes_all_checks(capsys):
    clean = (
        '<!DOCTYPE html><html lang="en"><head>'
        "<title>Quarterly Accessibility Audit Results</title></head>"
        "<body><main><h1>Results</h1><p>All clear.</p></main></body></html>"
    )
    # Write to a temp file via stdin-like path is not supported, so exercise
    # through a file the loader can read.
    import tempfile

    with tempfile.NamedTemporaryFile(
        "w", suffix=".html", delete=False, encoding="utf-8"
    ) as handle:
        handle.write(clean)
        path = handle.name

    exit_code = main(["--file", path, "--fail-on", "error"])
    out = capsys.readouterr().out
    assert exit_code == EXIT_OK
    assert "No automated issues detected." in out
