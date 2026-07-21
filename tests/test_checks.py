"""Unit tests for the individual accessibility checks."""

from __future__ import annotations

import pathlib

import pytest
from bs4 import BeautifulSoup

from section508checker.checks import run_all
from section508checker.checks.base import Severity
from section508checker.checks.color import (
    contrast_ratio,
    parse_color,
    relative_luminance,
)
from section508checker.checks.contrast import ColorContrastCheck
from section508checker.checks.document import (
    DocumentLanguageCheck,
    PageTitleCheck,
)
from section508checker.checks.forms import FormLabelCheck
from section508checker.checks.frames import FrameTitleCheck
from section508checker.checks.headings import HeadingStructureCheck
from section508checker.checks.images import ImageAltTextCheck
from section508checker.checks.links import LinkTextCheck
from section508checker.checks.tables import TableHeaderCheck

FIXTURE = pathlib.Path(__file__).parent / "fixtures" / "sample_inaccessible.html"


def _soup(markup: str) -> BeautifulSoup:
    return BeautifulSoup(markup, "html.parser")


@pytest.fixture
def sample() -> BeautifulSoup:
    return _soup(FIXTURE.read_text(encoding="utf-8"))


def test_missing_alt_is_flagged_but_decorative_and_described_pass(sample):
    findings = ImageAltTextCheck().run(sample)
    assert len(findings) == 1
    assert findings[0].criterion == "1.1.1"
    assert findings[0].severity is Severity.ERROR
    assert "banner.png" in findings[0].snippet


def test_missing_lang_flagged():
    findings = DocumentLanguageCheck().run(_soup("<html><body></body></html>"))
    assert len(findings) == 1
    assert findings[0].criterion == "3.1.1"


def test_valid_lang_passes():
    findings = DocumentLanguageCheck().run(_soup('<html lang="en"></html>'))
    assert findings == []


def test_generic_title_is_warning(sample):
    findings = PageTitleCheck().run(sample)
    assert len(findings) == 1
    assert findings[0].severity is Severity.WARNING


def test_missing_title_is_error():
    findings = PageTitleCheck().run(_soup("<html><head></head></html>"))
    assert len(findings) == 1
    assert findings[0].severity is Severity.ERROR


def test_unlabelled_input_flagged_labelled_passes(sample):
    findings = FormLabelCheck().run(sample)
    assert len(findings) == 1
    assert "search" in findings[0].snippet
    assert "placeholder" in findings[0].message.lower()


def test_aria_label_satisfies_form_check():
    findings = FormLabelCheck().run(
        _soup('<input type="text" aria-label="Search the site">')
    )
    assert findings == []


def test_heading_skip_flagged(sample):
    findings = HeadingStructureCheck().run(sample)
    assert len(findings) == 1
    assert "h1" in findings[0].message and "h3" in findings[0].message


def test_first_heading_not_h1_flagged():
    findings = HeadingStructureCheck().run(_soup("<h2>Section</h2>"))
    assert len(findings) == 1
    assert "h1" in findings[0].message.lower()


def test_empty_and_generic_links(sample):
    findings = LinkTextCheck().run(sample)
    severities = {f.severity for f in findings}
    assert Severity.ERROR in severities  # empty link
    assert Severity.WARNING in severities  # "click here"
    assert len(findings) == 2


def test_link_with_image_alt_passes():
    findings = LinkTextCheck().run(
        _soup('<a href="/home"><img src="/i.png" alt="Home"></a>')
    )
    assert findings == []


def test_table_without_headers_flagged(sample):
    findings = TableHeaderCheck().run(sample)
    assert len(findings) == 1
    assert findings[0].severity is Severity.WARNING


def test_presentation_table_skipped():
    findings = TableHeaderCheck().run(
        _soup('<table role="presentation"><tr><td>x</td></tr></table>')
    )
    assert findings == []


def test_iframe_without_title_flagged(sample):
    findings = FrameTitleCheck().run(sample)
    assert len(findings) == 1
    assert findings[0].criterion == "4.1.2"


def test_iframe_with_title_passes():
    findings = FrameTitleCheck().run(
        _soup('<iframe src="/w" title="Live chat"></iframe>')
    )
    assert findings == []


def test_parse_color_supports_hex_rgb_and_named():
    assert parse_color("#fff") == (255, 255, 255, 1.0)
    assert parse_color("#000000") == (0, 0, 0, 1.0)
    assert parse_color("rgb(255, 0, 0)") == (255, 0, 0, 1.0)
    assert parse_color("rgba(0, 0, 0, 0.5)") == (0, 0, 0, 0.5)
    assert parse_color("white") == (255, 255, 255, 1.0)
    assert parse_color("hsl(0, 100%, 50%)") is None  # unsupported -> skipped


def test_contrast_ratio_black_on_white_is_maximal():
    assert round(contrast_ratio((0, 0, 0), (255, 255, 255)), 1) == 21.0
    # Ratio is symmetric regardless of which colour is foreground.
    assert contrast_ratio((255, 255, 255), (0, 0, 0)) == contrast_ratio(
        (0, 0, 0), (255, 255, 255)
    )


def test_relative_luminance_bounds():
    assert relative_luminance((0, 0, 0)) == 0.0
    assert round(relative_luminance((255, 255, 255)), 4) == 1.0


def test_low_contrast_inline_text_flagged_high_contrast_passes(sample):
    findings = ColorContrastCheck().run(sample)
    assert len(findings) == 1
    assert findings[0].criterion == "1.4.3"
    assert findings[0].severity is Severity.ERROR
    assert "#888888" in findings[0].message
    assert "4.5:1 for normal text" in findings[0].message


def test_contrast_skips_when_background_indeterminate():
    # Foreground only, no resolvable background -> cannot assess -> skipped.
    findings = ColorContrastCheck().run(_soup('<p style="color:#777">Text</p>'))
    assert findings == []


def test_contrast_large_text_uses_relaxed_threshold():
    # #808080 on white is ~3.95:1 — fails normal text (4.5) but passes large (3.0).
    style = "color:#808080; background-color:#ffffff"
    assert ColorContrastCheck().run(_soup(f'<p style="{style}">Body</p>')) != []
    large = f'<p style="{style}; font-size:24px">Heading</p>'
    assert ColorContrastCheck().run(_soup(large)) == []


def test_run_all_aggregates_counts(sample):
    findings, checks_run, checks_passed = run_all(sample)
    assert checks_run == 9
    # Every check in the fixture produces at least one finding.
    assert checks_passed == 0
    assert len(findings) >= 9
