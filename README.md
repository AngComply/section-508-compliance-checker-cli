# Section 508 Compliance Checker CLI

> A command-line tool for automated detection of common Section 508 / WCAG accessibility barriers in web content.

[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![Standard: Section 508](https://img.shields.io/badge/standard-Section%20508-brightgreen.svg)](https://www.section508.gov/)
[![WCAG 2.1 AA](https://img.shields.io/badge/WCAG-2.1%20AA-brightgreen.svg)](https://www.w3.org/TR/WCAG21/)

---

## About

The **Section 508 Compliance Checker CLI** is the first project in my Section 508
SME and Compliance Analyst portfolio. It automates the detection of common
accessibility issues in HTML content so that audits move faster and remediation
starts sooner.

The tool inspects rendered pages for the kinds of defects that map directly to
the [Revised Section 508 Standards](https://www.access-board.gov/ict/) — which
incorporate [WCAG 2.0 Level A and AA](https://www.w3.org/TR/WCAG20/) success
criteria by reference. Because many current federal procurements and agency
policies now call for [WCAG 2.1 Level AA](https://www.w3.org/TR/WCAG21/), checks
are mapped to WCAG 2.1 as well (2.1 is backward-compatible with 2.0), and each
finding produces a structured, human-readable report an analyst can act on.

> **Scope note:** Automated tooling can reliably flag a subset of accessibility
> failures (roughly 30–40% of WCAG success criteria). It is a force multiplier
> for a human evaluator, not a replacement for manual testing with assistive
> technology. This tool is built to surface high-signal, machine-detectable
> issues and to document what still requires manual review.

## Features

- **Automated page analysis** — loads a live URL or local HTML file and scans
  the rendered DOM.
- **Checks mapped to Section 508 / WCAG success criteria**, including:
  - Missing or empty `alt` text on images (WCAG 1.1.1)
  - Form inputs without associated labels (WCAG 1.3.1, 4.1.2)
  - Missing document `lang` attribute (WCAG 3.1.1)
  - Missing or non-descriptive page `<title>` (WCAG 2.4.2)
  - Improper heading structure / skipped heading levels (WCAG 1.3.1, 2.4.6)
  - Links with no discernible text (WCAG 2.4.4)
  - Tables missing header associations (WCAG 1.3.1)
  - `iframe` elements without a `title` (WCAG 4.1.2)
- **Two rendering backends:**
  - **BeautifulSoup** for fast static-HTML parsing
  - **Selenium** for JavaScript-rendered pages and dynamic content
- **Structured reporting** — results grouped by severity with the mapped
  success criterion, element location, and remediation guidance.
- **Multiple output formats** — console, JSON, and Markdown for inclusion in
  audit deliverables.
- **CI-friendly exit codes** — non-zero exit on violations for use in build
  pipelines.

## Tech Stack

| Component | Purpose |
| --- | --- |
| **Python 3.10+** | Core language |
| **Selenium** | Browser automation for JS-rendered pages |
| **BeautifulSoup** | HTML parsing for static content |
| **argparse** | Command-line interface |

## Installation

> **Status:** This project is under active development. The commands below
> reflect the intended interface; see [Roadmap](#roadmap) for current status.

```bash
# Clone the repository
git clone https://github.com/<your-username>/section-508-cli-tool.git
cd section-508-cli-tool

# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

Selenium requires a browser driver. The tool targets Chrome/Chromium via
`chromedriver`. Install a matching driver and ensure it is on your `PATH`, or
let [`webdriver-manager`](https://pypi.org/project/webdriver-manager/) resolve
it automatically.

## Usage

```bash
# Scan a live URL (static parsing)
python checker.py --url https://example.gov

# Scan a JavaScript-rendered page (Selenium backend)
python checker.py --url https://example.gov --render selenium

# Scan a local HTML file
python checker.py --file ./page.html

# Emit a JSON report to a file
python checker.py --url https://example.gov --format json --output report.json

# Emit a Markdown report for an audit deliverable
python checker.py --url https://example.gov --format markdown --output findings.md
```

### Options

| Flag | Description |
| --- | --- |
| `--url <url>` | Target URL to scan |
| `--file <path>` | Local HTML file to scan |
| `--render {static,selenium}` | Rendering backend (default: `static`) |
| `--format {console,json,markdown}` | Report format (default: `console`) |
| `--output <path>` | Write the report to a file instead of stdout |
| `--fail-on {any,error}` | Exit non-zero when issues are found (CI use) |

### Example output

```
Section 508 Compliance Report — https://example.gov
============================================================
[ERROR]  1.1.1  Non-text Content
         <img src="/logo.png"> is missing an alt attribute
         → Add descriptive alt text, or alt="" if decorative.

[WARN]   2.4.2  Page Titled
         Document <title> is generic ("Home")
         → Use a unique, descriptive title for each page.

Summary: 1 error, 1 warning, 6 checks passed
```

## How this maps to compliance work

Each finding is tied to a specific WCAG success criterion referenced by the
Revised Section 508 Standards, so results drop directly into an
**Accessibility Conformance Report (ACR / VPAT)** workflow. The tool is designed
to complement — not replace — manual evaluation with screen readers (JAWS,
NVDA, VoiceOver), keyboard-only navigation, and color-contrast analysis.

## Roadmap

- [ ] Core checker engine (`checker.py`) and check modules
- [ ] `requirements.txt` and pinned dependencies
- [ ] BeautifulSoup static backend
- [ ] Selenium dynamic backend
- [ ] JSON and Markdown reporters
- [ ] Color-contrast analysis (WCAG 1.4.3 / 1.4.11)
- [ ] Unit tests and sample fixtures
- [ ] CI workflow

## Portfolio context

This tool is part of a broader portfolio demonstrating hands-on Section 508
testing and remediation capability. See [docs/Portfolio.md](docs/Portfolio.md)
for the full portfolio overview.

## Disclaimer

Automated results are advisory. A conformance determination requires manual
testing by a qualified evaluator. This tool does not certify Section 508
compliance.

## License

To be determined.
