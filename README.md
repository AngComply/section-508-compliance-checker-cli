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
  - Insufficient text/background color contrast (WCAG 1.4.3) — full-page under
    `--render selenium`, inline styles otherwise; see the note under
    [Roadmap](#roadmap)
  - Low-contrast form-field boundaries (WCAG 1.4.11 Non-text Contrast) —
    full-page under `--render selenium`, inline otherwise
  - Missing or duplicate main landmark (WCAG 1.3.1)
  - Duplicate banner / contentinfo landmarks (WCAG 1.3.1)
  - Multiple navigation landmarks without accessible names (WCAG 1.3.1)
  - Missing skip link when navigation is present (WCAG 2.4.1)
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

Requires **Python 3.10+**.

```bash
# Clone the repository
git clone https://github.com/AngComply/section-508-compliance-checker-cli.git
cd section-508-compliance-checker-cli

# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

The `--render selenium` backend drives headless **Chrome/Chromium**, which must
be installed on the host. The matching driver is resolved automatically by
[Selenium Manager](https://www.selenium.dev/documentation/selenium_manager/)
(bundled with Selenium 4.6+), so no separate `chromedriver` install is required.
The static backend (the default) needs no browser at all.

To run the test suite, install the development dependencies instead:

```bash
pip install -r requirements-dev.txt
pytest
```

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
| `--fail-on {error,any,none}` | Exit non-zero when issues are found — `error` (default) fails on errors, `any` on any finding, `none` never fails (CI use) |
| `--timeout <seconds>` | Network timeout for URL fetches (default: 30) |

### Example output

```
Section 508 Compliance Report — https://example.gov
============================================================
[ERROR]  1.1.1  Non-text Content
        Image is missing an alt attribute.
        <img src="/logo.png"/>
        → Add descriptive alt text, or alt="" if the image is purely decorative.

[WARNING]  2.4.2  Page Titled
        The page title 'Home' is generic and non-descriptive.
        <title>
        → Use a specific title that distinguishes this page from others.

------------------------------------------------------------
Summary: 1 error, 1 warning, 6 of 8 checks passed
```

## How this maps to compliance work

Each finding is tied to a specific WCAG success criterion referenced by the
Revised Section 508 Standards, so results drop directly into an
**Accessibility Conformance Report (ACR / VPAT)** workflow. The tool is designed
to complement — not replace — manual evaluation with screen readers (JAWS,
NVDA, VoiceOver), keyboard-only navigation, and color-contrast analysis.

## Roadmap

- [x] Core checker engine (`checker.py`) and check modules
- [x] `requirements.txt` and pinned dependencies
- [x] BeautifulSoup static backend
- [x] Selenium dynamic backend
- [x] JSON and Markdown reporters
- [x] Unit tests and sample fixtures
- [x] CI workflow (GitHub Actions: ruff lint + pytest matrix)
- [x] Color-contrast analysis (WCAG 1.4.3) — full-page (Selenium computed
      styles) and inline (static)
- [x] Landmark checks — main, banner/contentinfo uniqueness, navigation
      naming, skip link (WCAG 1.3.1 / 2.4.1)
- [x] Non-text contrast for form fields (WCAG 1.4.11)
- [ ] Non-text contrast for icons, graphics, and focus indicators (broader
      WCAG 1.4.11)
- [ ] Pixel-sampling for backgrounds painted by overlays, `::before`
      pseudo-elements, or images that lie outside the text's ancestor chain
      (current contrast checks skip these rather than guess)

Fourteen checks ship today, mapped to WCAG 1.1.1, 1.3.1, 1.4.3, 1.4.11, 2.4.1,
2.4.2, 2.4.4, 3.1.1, and 4.1.2. See the source in
[`section508checker/checks/`](section508checker/checks/).

> **Color-contrast scope:** With `--render selenium`, the check reads each text
> element's real rendered color and background via `getComputedStyle`, so it
> evaluates the full page regardless of where the styles come from (inline,
> embedded, external, or inherited). Semi-transparent background layers are
> composited down to the first opaque color. When the effective background can't
> be resolved to a single color — e.g. text over a CSS gradient or background
> image — the element is skipped rather than compared against a guessed color,
> so the check avoids false positives at the cost of coverage on those elements.
> Without a browser (static / file input), only inline `style` attributes are
> visible, so an element is assessed only when both its foreground and an opaque
> background are determinable inline. For the most complete results, run with
> `--render selenium`.

## Portfolio context

This tool is part of a broader portfolio demonstrating hands-on Section 508
testing and remediation capability. See [docs/Portfolio.md](docs/Portfolio.md)
for the full portfolio overview.

## Disclaimer

Automated results are advisory. A conformance determination requires manual
testing by a qualified evaluator. This tool does not certify Section 508
compliance.

## License

Released under the [MIT License](LICENSE).
