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

# Three text elements whose backgrounds come from CSS gradients — which the DOM
# cannot resolve to a single colour, so they exercise the pixel-sampling path:
#   1. white on a DARK gradient  -> real background is dark -> passes
#   2. grey on a LIGHT gradient  -> genuinely low contrast  -> flagged
#      (this case was previously skipped; only pixel sampling detects it)
# plus a solid low-contrast paragraph the DOM resolves directly -> flagged.
_PAGE = """<!DOCTYPE html>
<html lang="en">
  <head><title>Contrast Pixel-Sampling Fixture</title></head>
  <body style="background:#ffffff">
    <div style="background-image:linear-gradient(#0a1a2a,#0a1a2a); padding:24px">
      <p style="color:#ffffff; font-size:16px">White text on dark gradient</p>
    </div>
    <div style="background-image:linear-gradient(#f0f0f0,#f0f0f0); padding:24px">
      <p style="color:#c8c8c8; font-size:16px">Low contrast over gradient</p>
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


def test_white_on_dark_gradient_passes_via_pixels(tmp_path):
    # Pixel sampling reads the real dark background, so the white text passes.
    assert "White text on dark gradient" not in _contrast_snippets(tmp_path)


def test_low_contrast_over_gradient_flagged_via_pixels(tmp_path):
    # The DOM cannot resolve a gradient background; pixel sampling recovers the
    # light colour and correctly flags this genuinely low-contrast text.
    assert "Low contrast over gradient" in _contrast_snippets(tmp_path)
