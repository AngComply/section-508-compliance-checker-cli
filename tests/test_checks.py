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
from section508checker.checks.contrast import ColorContrastCheck, required_ratio
from section508checker.checks.document import (
    DocumentLanguageCheck,
    PageTitleCheck,
)
from section508checker.checks.forms import FormLabelCheck
from section508checker.checks.frames import FrameTitleCheck
from section508checker.checks.headings import HeadingStructureCheck
from section508checker.checks.images import ImageAltTextCheck
from section508checker.checks.landmarks import (
    LandmarkUniquenessCheck,
    MainLandmarkCheck,
    NavigationNameCheck,
    SkipLinkCheck,
)
from section508checker.checks.links import LinkTextCheck
from section508checker.checks.nontext_contrast import NonTextContrastCheck
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


def test_missing_main_landmark_is_warning(sample):
    findings = MainLandmarkCheck().run(sample)
    assert len(findings) == 1
    assert findings[0].severity is Severity.WARNING


def test_single_main_landmark_passes():
    assert MainLandmarkCheck().run(_soup("<body><main>Content</main></body>")) == []
    assert MainLandmarkCheck().run(_soup('<div role="main">Content</div>')) == []


def test_multiple_main_landmarks_is_error():
    findings = MainLandmarkCheck().run(
        _soup("<body><main>A</main><main>B</main></body>")
    )
    assert len(findings) == 1
    assert findings[0].severity is Severity.ERROR
    assert "2 main landmarks" in findings[0].message


def test_skip_link_missing_with_nav_is_warning(sample):
    findings = SkipLinkCheck().run(sample)
    assert len(findings) == 1
    assert findings[0].criterion == "2.4.1"


def test_skip_link_present_passes():
    markup = (
        '<body><a href="#main">Skip to main content</a>'
        '<nav><a href="/a">A</a></nav></body>'
    )
    assert SkipLinkCheck().run(_soup(markup)) == []


def test_skip_link_not_flagged_without_navigation():
    # No navigation landmark -> nothing to bypass -> no warning.
    assert SkipLinkCheck().run(_soup("<body><p>Just text</p></body>")) == []


def test_single_banner_and_contentinfo_pass():
    markup = "<body><header>Top</header><main>x</main><footer>Bottom</footer></body>"
    assert LandmarkUniquenessCheck().run(_soup(markup)) == []


def test_duplicate_banner_and_contentinfo_flagged(sample):
    findings = LandmarkUniquenessCheck().run(sample)
    # Fixture has two <header> and two <footer> at top level.
    assert len(findings) == 2
    assert all(f.severity is Severity.ERROR for f in findings)
    messages = " ".join(f.message for f in findings)
    assert "banner landmarks" in messages
    assert "contentinfo landmarks" in messages


def test_nested_header_footer_are_not_landmarks():
    # <header>/<footer> inside sectioning content are not banner/contentinfo.
    markup = (
        "<body><header>Site</header>"
        "<article><header>Article head</header><footer>Article foot</footer></article>"
        "<footer>Site foot</footer></body>"
    )
    assert LandmarkUniquenessCheck().run(_soup(markup)) == []


def test_single_nav_needs_no_name():
    assert NavigationNameCheck().run(_soup("<nav><a href='/a'>A</a></nav>")) == []


def test_multiple_unnamed_navs_flagged(sample):
    findings = NavigationNameCheck().run(sample)
    assert len(findings) == 1
    assert findings[0].severity is Severity.WARNING
    assert "navigation landmarks" in findings[0].message


def test_multiple_named_navs_pass():
    markup = (
        '<body><nav aria-label="Primary"><a href="/a">A</a></nav>'
        '<nav aria-label="Footer"><a href="/b">B</a></nav></body>'
    )
    assert NavigationNameCheck().run(_soup(markup)) == []


def test_nontext_contrast_low_border_flagged_inline(sample):
    findings = NonTextContrastCheck().run(sample)
    assert len(findings) == 1
    assert findings[0].criterion == "1.4.11"
    assert findings[0].severity is Severity.WARNING


def test_nontext_contrast_strong_border_passes_inline():
    # A dark border (#595959, ~7:1 on white) makes the field perceivable.
    markup = (
        '<div style="background-color:#ffffff">'
        '<input aria-label="x" style="border:1px solid #595959;'
        'background-color:#ffffff"></div>'
    )
    assert NonTextContrastCheck().run(_soup(markup)) == []


def test_nontext_contrast_fill_difference_passes_inline():
    # No border, but a dark fill on a white page delineates the field.
    markup = (
        '<div style="background-color:#ffffff">'
        '<input aria-label="x" style="border:none;'
        'background-color:#333333"></div>'
    )
    assert NonTextContrastCheck().run(_soup(markup)) == []


def test_nontext_contrast_skips_without_resolvable_surround():
    # No inline background anywhere -> surrounding colour unknown -> skip.
    markup = '<input aria-label="x" style="border:1px solid #dddddd">'
    assert NonTextContrastCheck().run(_soup(markup)) == []


def test_nontext_contrast_computed_mode():
    check = NonTextContrastCheck()
    check.component_styles = [
        {  # light border + white fill on white page -> imperceptible
            "borderColor": "rgb(221, 221, 221)",
            "borderStyle": "solid",
            "borderWidth": 1,
            "background": "rgb(255, 255, 255)",
            "boxShadow": "none",
            "surround": "rgb(255, 255, 255)",
            "snippet": "<input>",
        },
        {  # strong border -> perceivable, no finding
            "borderColor": "rgb(89, 89, 89)",
            "borderStyle": "solid",
            "borderWidth": 1,
            "background": "rgb(255, 255, 255)",
            "boxShadow": "none",
            "surround": "rgb(255, 255, 255)",
            "snippet": "<input>",
        },
    ]
    findings = check.run(None)
    assert len(findings) == 1
    assert findings[0].criterion == "1.4.11"


def test_required_ratio_thresholds():
    assert required_ratio(None, bold=False) == 4.5  # unknown -> stricter
    assert required_ratio(16.0, bold=False) == 4.5  # normal text
    assert required_ratio(24.0, bold=False) == 3.0  # >= 24px is large
    assert required_ratio(19.0, bold=True) == 3.0  # >= 18.66px bold is large
    assert required_ratio(19.0, bold=False) == 4.5  # not bold -> still normal


def _computed(color, background, size=16, weight=400, snippet="<p>x</p>"):
    return {
        "color": color,
        "background": background,
        "fontSize": size,
        "fontWeight": weight,
        "snippet": snippet,
    }


def test_computed_mode_flags_low_contrast_and_passes_high():
    check = ColorContrastCheck()
    check.computed_styles = [
        _computed("rgb(119, 119, 119)", "rgb(136, 136, 136)"),  # ~1.26:1 fail
        _computed("rgb(0, 0, 0)", "rgb(255, 255, 255)"),  # 21:1 pass
    ]
    findings = check.run(None)  # soup is unused in computed mode
    assert len(findings) == 1
    assert findings[0].criterion == "1.4.3"


def test_computed_mode_large_text_uses_relaxed_threshold():
    check = ColorContrastCheck()
    # ~3.95:1 fails normal but passes large text.
    check.computed_styles = [
        _computed("rgb(128, 128, 128)", "rgb(255, 255, 255)", size=24)
    ]
    assert check.run(None) == []


def test_computed_mode_composites_translucent_foreground():
    check = ColorContrastCheck()
    # Fully transparent text over white composites to white -> ratio 1:1 -> fail.
    check.computed_styles = [_computed("rgba(0, 0, 0, 0)", "rgb(255, 255, 255)")]
    findings = check.run(None)
    assert len(findings) == 1


def test_run_all_threads_computed_styles_to_contrast():
    # A clean page (no inline issues) but a failing computed record.
    clean = _soup('<html lang="en"><head><title>Clean Page</title></head></html>')
    records = [_computed("rgb(119, 119, 119)", "rgb(136, 136, 136)")]
    findings, _, _ = run_all(clean, computed_styles=records)
    assert any(f.criterion == "1.4.3" for f in findings)


def test_run_all_deduplicates_identical_findings():
    # The same component failing identically several times collapses to one.
    clean = _soup('<html lang="en"><head><title>Clean Page</title></head></html>')
    dup = _computed("rgb(120, 120, 120)", "rgb(255, 255, 255)", snippet="<p>Same</p>")
    findings, _, _ = run_all(clean, computed_styles=[dup, dup, dup])
    contrast = [f for f in findings if f.criterion == "1.4.3"]
    assert len(contrast) == 1


def test_run_all_aggregates_counts(sample):
    findings, checks_run, checks_passed = run_all(sample)
    assert checks_run == 14
    # Every check in the fixture produces at least one finding.
    assert checks_passed == 0
    assert len(findings) >= 14
