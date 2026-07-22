"""HTML acquisition for the checker.

Three sources are supported:
  * a local file,
  * a live URL fetched as static HTML (``requests``),
  * a live URL rendered in a headless browser (``selenium``) for pages whose
    content is produced by JavaScript.

The Selenium backend additionally captures *computed* text styles from the live
DOM (via ``getComputedStyle``), which enables full-page colour-contrast
evaluation that inline-only static parsing cannot provide.

Third-party backends are imported lazily so that file/static usage does not
require Selenium to be installed, and vice versa. Every failure mode is raised
as :class:`LoaderError` with an actionable message.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

DEFAULT_TIMEOUT = 30
_USER_AGENT = "section-508-compliance-checker/0.1 (+accessibility audit)"


class LoaderError(Exception):
    """Raised when HTML cannot be acquired from the requested source."""


@dataclass
class LoadedPage:
    """The result of loading a page.

    Attributes:
        html: The page's HTML source.
        computed_styles: One record per text-bearing element with its
            browser-computed colours and font metrics, or ``None`` when the
            source cannot provide computed styles (file/static backends).
        component_styles: One record per editable form control with its
            browser-computed border, background, and surrounding background,
            used for non-text contrast (WCAG 1.4.11). ``None`` for non-browser
            backends.
        graphic_styles: One record per meaningful (non-decorative) SVG graphic
            with its fill/stroke and background, for non-text contrast (1.4.11).
        focus_states: One record per keyboard-focusable element with its
            focus-state styles, for focus visibility (WCAG 2.4.7).
    """

    html: str
    computed_styles: list[dict] | None = None
    component_styles: list[dict] | None = None
    graphic_styles: list[dict] | None = None
    focus_states: list[dict] | None = None


# JavaScript executed in the live page to collect computed text styles. For each
# element that directly contains visible text, it records the computed colour,
# the nearest non-transparent ancestor background, and font metrics.
#
# effectiveBackground resolves the nearest opaque ancestor background colour, or
# returns null when it cannot: if any ancestor paints a gradient/image background
# (backgroundImage != 'none'), or if no ancestor sets an explicit opaque
# background at all (e.g. Tailwind gradient heroes, or dark cards whose colour
# comes from an absolutely-positioned overlay or ::before pseudo-element that is
# not in the text's ancestor chain). Rather than guess, the loader resolves those
# null cases by sampling the actual rendered pixels from a page screenshot.
_COMPUTED_STYLES_JS = r"""
function parseRgb(value) {
  const m = value && value.match(/rgba?\(([^)]+)\)/);
  if (!m) return null;
  const p = m[1].split(',').map(function (s) { return parseFloat(s); });
  return { r: p[0], g: p[1], b: p[2], a: p.length === 4 ? p[3] : 1 };
}
function effectiveBackground(el) {
  // Collect background-colour layers from the text element upward (front to
  // back) until an opaque one is reached, then composite them. Returns null
  // (indeterminate) if a gradient/image is encountered first, or if no opaque
  // base exists -- both cases cannot be resolved to a single colour.
  const layers = [];
  let node = el;
  while (node) {
    const cs = getComputedStyle(node);
    if (cs.backgroundImage && cs.backgroundImage !== 'none') {
      return null;  // gradient/image behind text: cannot resolve a solid colour
    }
    const c = parseRgb(cs.backgroundColor);
    if (c && c.a > 0) {
      layers.push(c);
      if (c.a >= 1) {  // opaque base reached: composite the stack over it
        let r = c.r, g = c.g, b = c.b;
        for (let i = layers.length - 2; i >= 0; i--) {
          const l = layers[i];
          r = Math.round(l.r * l.a + r * (1 - l.a));
          g = Math.round(l.g * l.a + g * (1 - l.a));
          b = Math.round(l.b * l.a + b * (1 - l.a));
        }
        return 'rgb(' + r + ', ' + g + ', ' + b + ')';
      }
    }
    node = node.parentElement;
  }
  return null;  // no opaque ancestor background: indeterminate, do not guess
}
const results = [];
const elements = document.body ? document.body.querySelectorAll('*') : [];
for (const el of elements) {
  let hasText = false;
  for (const child of el.childNodes) {
    if (child.nodeType === 3 && child.textContent.trim().length > 0) {
      hasText = true;
      break;
    }
  }
  if (!hasText) continue;
  const cs = getComputedStyle(el);
  if (cs.visibility === 'hidden' || cs.display === 'none') continue;
  // background may be null (indeterminate): the loader then resolves it by
  // sampling the actual rendered pixels from a screenshot, using the rect.
  const background = effectiveBackground(el);
  const rect = el.getBoundingClientRect();
  results.push({
    color: cs.color,
    background: background,
    fontSize: parseFloat(cs.fontSize),
    fontWeight: parseInt(cs.fontWeight, 10) || 400,
    snippet: (el.outerHTML || '').slice(0, 200),
    rect: { x: rect.left, y: rect.top, w: rect.width, h: rect.height },
  });
}
// Editable text fields, for non-text contrast (WCAG 1.4.11).
const TEXT_INPUT_TYPES = [
  '', 'text', 'email', 'password', 'search', 'tel', 'url', 'number',
  'date', 'datetime-local', 'month', 'week', 'time',
];
const components = [];
const controls = document.body
  ? document.body.querySelectorAll('input, select, textarea')
  : [];
for (const el of controls) {
  if (el.tagName === 'INPUT' && !TEXT_INPUT_TYPES.includes(el.type)) continue;
  const cs = getComputedStyle(el);
  if (cs.visibility === 'hidden' || cs.display === 'none') continue;
  components.push({
    borderColor: cs.borderTopColor,
    borderStyle: cs.borderTopStyle,
    borderWidth: parseFloat(cs.borderTopWidth) || 0,
    background: cs.backgroundColor,
    boxShadow: cs.boxShadow,
    surround: effectiveBackground(el.parentElement || el),
    snippet: (el.outerHTML || '').slice(0, 200),
  });
}
// Meaningful (non-decorative) SVG graphics, for non-text contrast (1.4.11).
// A graphic is in scope only if it exposes an accessible name / img role; a
// decorative icon (aria-hidden / role=presentation / unnamed) is exempt.
const graphics = [];
const svgs = document.body ? document.body.querySelectorAll('svg') : [];
for (const el of svgs) {
  const role = (el.getAttribute('role') || '').toLowerCase();
  if (el.getAttribute('aria-hidden') === 'true') continue;
  if (role === 'presentation' || role === 'none') continue;
  const named =
    (el.getAttribute('aria-label') || '').trim() ||
    el.getAttribute('aria-labelledby') ||
    role === 'img' ||
    el.querySelector('title');
  if (!named) continue;
  const cs = getComputedStyle(el);
  if (cs.visibility === 'hidden' || cs.display === 'none') continue;
  const rect = el.getBoundingClientRect();
  if (rect.width < 1 || rect.height < 1) continue;
  graphics.push({
    fill: cs.fill,
    stroke: cs.stroke,
    background: effectiveBackground(el.parentElement || el),
    snippet: (el.outerHTML || '').slice(0, 160),
    rect: { x: rect.left, y: rect.top, w: rect.width, h: rect.height },
  });
}
return {
  text: results,
  components: components,
  graphics: graphics,
  devicePixelRatio: window.devicePixelRatio || 1,
};
"""

# Executed after each Tab keypress to read the keyboard-focused element and its
# focus-state styles (real keyboard focus, so :focus-visible rules apply).
_FOCUS_PROBE_JS = r"""
const el = document.activeElement;
if (!el || el === document.body || el === document.documentElement) {
  return { done: true };
}
if (el.getAttribute('data-a11y-focus-seen')) {
  return { done: true };  // focus has cycled back to a visited element
}
el.setAttribute('data-a11y-focus-seen', '1');
const cs = getComputedStyle(el);
return {
  done: false,
  outlineStyle: cs.outlineStyle,
  outlineWidth: cs.outlineWidth,
  outlineColor: cs.outlineColor,
  boxShadow: cs.boxShadow,
  snippet: (el.outerHTML || '').slice(0, 160),
};
"""


def load_html(
    *,
    url: str | None = None,
    file: str | None = None,
    render: str = "static",
    timeout: int = DEFAULT_TIMEOUT,
) -> LoadedPage:
    """Return the loaded page for the requested source.

    Exactly one of ``url`` or ``file`` must be provided.
    """
    if file:
        return LoadedPage(html=_load_file(file))
    if url:
        if render == "selenium":
            return _load_selenium(url, timeout)
        return LoadedPage(html=_load_static(url, timeout))
    raise LoaderError("No input source provided; supply a URL or a file path.")


def _load_file(file: str) -> str:
    path = Path(file)
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise LoaderError(f"File not found: {file}") from exc
    except IsADirectoryError as exc:
        raise LoaderError(f"Expected a file but got a directory: {file}") from exc
    except UnicodeDecodeError as exc:
        raise LoaderError(
            f"File is not valid UTF-8 text and could not be read: {file}"
        ) from exc
    except OSError as exc:
        raise LoaderError(f"Could not read file {file}: {exc}") from exc


def _load_static(url: str, timeout: int) -> str:
    try:
        import requests
    except ImportError as exc:  # pragma: no cover - depends on environment
        raise LoaderError(
            "The 'requests' package is required to fetch URLs. Install it with "
            "'pip install -r requirements.txt'."
        ) from exc

    try:
        response = requests.get(
            url,
            timeout=timeout,
            headers={"User-Agent": _USER_AGENT},
        )
        response.raise_for_status()
    except requests.exceptions.MissingSchema as exc:
        raise LoaderError(
            f"'{url}' is not a valid URL. Include the scheme, e.g. https://example.gov."
        ) from exc
    except requests.exceptions.Timeout as exc:
        raise LoaderError(f"Timed out after {timeout}s fetching {url}.") from exc
    except requests.exceptions.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else "?"
        raise LoaderError(f"Server returned HTTP {status} for {url}.") from exc
    except requests.exceptions.ConnectionError as exc:
        raise LoaderError(f"Could not connect to {url}.") from exc
    except requests.exceptions.RequestException as exc:
        raise LoaderError(f"Failed to fetch {url}: {exc}") from exc

    return response.text


def _resolve_backgrounds_from_pixels(
    records: list[dict], screenshot: bytes, device_pixel_ratio: float
) -> None:
    """Fill in ``background`` for records the DOM could not resolve.

    Mutates ``records`` in place: for each text record whose ``background`` is
    None, sample the screenshot at its rect to recover the real painted colour.
    Records that remain unresolved keep ``background = None`` and are skipped by
    the contrast check (never guessed).
    """
    from .pixels import dominant_background

    for record in records:
        if record.get("background") is not None:
            continue
        rect = record.get("rect")
        if not rect:
            continue
        record["background"] = dominant_background(screenshot, rect, device_pixel_ratio)


def _collect_focus_states(driver, max_tabs: int = 250) -> list[dict]:
    """Tab through the page and record each focusable element's focus styles.

    Uses real keyboard focus (Tab), so ``:focus-visible`` rules apply — the
    accurate signal for whether a visible focus indicator is shown. Stops when
    focus leaves the page or cycles back to an already-visited element.
    """
    from selenium.common.exceptions import WebDriverException
    from selenium.webdriver.common.keys import Keys

    states: list[dict] = []
    for _ in range(max_tabs):
        try:
            driver.switch_to.active_element.send_keys(Keys.TAB)
            info = driver.execute_script(_FOCUS_PROBE_JS)
        except WebDriverException:  # pragma: no cover - defensive
            break
        if not info or info.get("done"):
            break
        states.append(info)
    return states


def _load_selenium(url: str, timeout: int) -> LoadedPage:
    try:
        from selenium import webdriver
        from selenium.common.exceptions import WebDriverException
        from selenium.webdriver.chrome.options import Options
    except ImportError as exc:
        raise LoaderError(
            "The 'selenium' package is required for --render selenium. Install "
            "it with 'pip install -r requirements.txt'."
        ) from exc

    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-dev-shm-usage")

    driver = None
    try:
        driver = webdriver.Chrome(options=options)
        driver.set_page_load_timeout(timeout)
        driver.get(url)
        html = driver.page_source

        # Grow the viewport to the full document height and scroll to the top so
        # a single screenshot captures the whole page for pixel sampling.
        page_height = driver.execute_script(
            "return Math.max(document.body.scrollHeight, "
            "document.documentElement.scrollHeight);"
        )
        width = driver.execute_script("return document.documentElement.clientWidth;")
        driver.set_window_size(width or 1280, min(int(page_height or 0) + 100, 16000))
        driver.execute_script("window.scrollTo(0, 0);")

        extracted = driver.execute_script(_COMPUTED_STYLES_JS)
        text_records = extracted.get("text", [])
        graphic_records = extracted.get("graphics", [])
        dpr = extracted.get("devicePixelRatio", 1)
        try:
            screenshot = driver.get_screenshot_as_png()
        except WebDriverException:  # pragma: no cover - screenshot unsupported
            screenshot = None
        if screenshot is not None:
            _resolve_backgrounds_from_pixels(text_records, screenshot, dpr)
            _resolve_backgrounds_from_pixels(graphic_records, screenshot, dpr)

        focus_states = _collect_focus_states(driver)

        return LoadedPage(
            html=html,
            computed_styles=text_records,
            component_styles=extracted.get("components", []),
            graphic_styles=graphic_records,
            focus_states=focus_states,
        )
    except WebDriverException as exc:
        raise LoaderError(
            "Selenium could not render the page. Ensure Chrome/Chromium is "
            f"installed and reachable. Underlying error: {exc.msg or exc}"
        ) from exc
    finally:
        if driver is not None:
            driver.quit()
