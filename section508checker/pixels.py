"""Resolve an element's effective background by sampling rendered pixels.

When computed styles cannot determine the colour behind text (a gradient, a
background image, a ``::before`` pseudo-element, or an overlay outside the DOM
ancestor chain), the real answer is whatever is actually painted on screen. This
module reads those pixels from a page screenshot rather than guessing.

The dominant colour within a text element's box is, in practice, its background:
glyphs cover a minority of the area. Sampling therefore returns the most common
(lightly quantised) colour in the element's rectangle. Pillow is imported lazily
so the dependency is only needed for the Selenium pixel-sampling path.
"""

from __future__ import annotations

import io
from collections import Counter

# Quantise channels to this step before counting, to fold anti-aliasing noise
# into the dominant colour.
_QUANTIZE = 8
# Cap how many pixels we count per element (stride-sample larger boxes).
_MAX_SAMPLES = 4000


def dominant_background(
    png_bytes: bytes, rect: dict, device_pixel_ratio: float = 1.0
) -> str | None:
    """Return the dominant colour in ``rect`` as an ``rgb(r, g, b)`` string.

    ``rect`` holds CSS-pixel ``x``/``y``/``w``/``h`` (viewport-relative, taken at
    scroll position 0). Returns None if the region is empty or off-screen.
    """
    try:
        from PIL import Image
    except ImportError:  # pragma: no cover - depends on environment
        return None

    dpr = device_pixel_ratio or 1.0
    left = int(rect.get("x", 0) * dpr)
    top = int(rect.get("y", 0) * dpr)
    right = left + int(rect.get("w", 0) * dpr)
    bottom = top + int(rect.get("h", 0) * dpr)

    with Image.open(io.BytesIO(png_bytes)) as opened:
        image = opened.convert("RGB")
        width, height = image.size
        left = max(0, min(left, width))
        top = max(0, min(top, height))
        right = max(0, min(right, width))
        bottom = max(0, min(bottom, height))
        if right - left < 2 or bottom - top < 2:
            return None
        region = image.crop((left, top, right, bottom))
        # Raw RGB bytes: [r, g, b, r, g, b, ...] — version-stable and fast.
        raw = region.tobytes()

    pixel_count = len(raw) // 3
    if pixel_count == 0:
        return None
    stride = max(1, pixel_count // _MAX_SAMPLES)

    counts: Counter = Counter()
    for i in range(0, pixel_count, stride):
        offset = i * 3
        counts[
            (
                raw[offset] // _QUANTIZE * _QUANTIZE,
                raw[offset + 1] // _QUANTIZE * _QUANTIZE,
                raw[offset + 2] // _QUANTIZE * _QUANTIZE,
            )
        ] += 1
    (r, g, b), _ = counts.most_common(1)[0]
    return f"rgb({r}, {g}, {b})"
