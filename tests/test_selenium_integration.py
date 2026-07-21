"""Live browser integration tests for the Selenium full-page contrast path.

These drive real headless Chrome, so they are skipped automatically when no
Chrome/Chromium binary is available (e.g. in CI without a browser). Run them
locally after installing Google Chrome to exercise the ``getComputedStyle``
extraction and background-compositing logic end to end.
"""

from __future__ import annotations

import shutil

import pytest
from bs4 import BeautifulSoup

from section508checker.checks import run_all
from section508checker.loader import load_html

pytestmark = pytest.mark.skipif(
    not any(
        shutil.which(binary)
        for binary in (
            "google-chrome",
            "google-chrome-stable",
            "chromium",
            "chromium-browser",
        )
    ),
    reason="headless Chrome/Chromium not available",
)

# White text inside a 10%-white card over a dark gradient (should NOT be flagged
# — the effective background is dark), plus a solid low-contrast paragraph that
# SHOULD be flagged.
_PAGE = """<!DOCTYPE html>
<html lang="en">
  <head><title>Contrast Layering Fixture</title></head>
  <body style="background:#ffffff">
    <div style="background-image:linear-gradient(#0a1a2a,#0a1a2a); padding:24px">
      <div style="background-color:rgba(255,255,255,0.1); padding:24px">
        <p style="color:#ffffff; font-size:16px">White text on dark gradient</p>
      </div>
    </div>
    <p style="color:#888;background:#fff;font-size:16px">Solid low contrast</p>
  </body>
</html>
"""


def _contrast_snippets(tmp_path):
    page_file = tmp_path / "page.html"
    page_file.write_text(_PAGE, encoding="utf-8")
    page = load_html(url=page_file.as_uri(), render="selenium")
    assert page.computed_styles is not None
    soup = BeautifulSoup(page.html, "html.parser")
    findings, _, _ = run_all(soup, computed_styles=page.computed_styles)
    return " ".join(f.snippet for f in findings if f.criterion == "1.4.3")


def test_solid_low_contrast_is_flagged(tmp_path):
    assert "Solid low contrast" in _contrast_snippets(tmp_path)


def test_translucent_over_gradient_is_skipped(tmp_path):
    # The white text is readable on the dark gradient; the compositing logic must
    # resolve the effective background as indeterminate/dark and NOT flag it.
    assert "White text on dark gradient" not in _contrast_snippets(tmp_path)
