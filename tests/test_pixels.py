"""Unit tests for the pixel-sampling background resolver (no browser needed)."""

from __future__ import annotations

import io

from PIL import Image

from section508checker.pixels import dominant_background


def _png(color: tuple[int, int, int], size=(100, 40), speckle=None) -> bytes:
    """A solid-colour PNG, optionally with a few 'text' pixels of another colour."""
    image = Image.new("RGB", size, color)
    if speckle is not None:
        for x in range(0, size[0], 7):  # sparse minority pixels
            image.putpixel((x, size[1] // 2), speckle)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def test_dominant_returns_majority_background():
    # Dark background with a minority of white "text" pixels -> dark dominates.
    png = _png((8, 24, 80), speckle=(255, 255, 255))
    rect = {"x": 0, "y": 0, "w": 100, "h": 40}
    assert dominant_background(png, rect) == "rgb(8, 24, 80)"


def test_dominant_respects_device_pixel_ratio():
    png = _png((240, 240, 240), size=(200, 80))
    rect = {"x": 0, "y": 0, "w": 100, "h": 40}  # CSS px; ×2 covers the image
    assert dominant_background(png, rect, device_pixel_ratio=2) == "rgb(240, 240, 240)"


def test_offscreen_or_empty_rect_returns_none():
    png = _png((255, 255, 255))
    assert dominant_background(png, {"x": 999, "y": 999, "w": 50, "h": 50}) is None
    assert dominant_background(png, {"x": 0, "y": 0, "w": 0, "h": 0}) is None


def test_rect_is_clamped_to_image_bounds():
    # A rect extending past the image still samples the visible region.
    png = _png((100, 150, 200), size=(60, 30))
    rect = {"x": 0, "y": 0, "w": 500, "h": 500}
    assert dominant_background(png, rect) == "rgb(96, 144, 200)"  # quantised
