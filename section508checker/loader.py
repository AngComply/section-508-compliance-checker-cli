"""HTML acquisition for the checker.

Three sources are supported:
  * a local file,
  * a live URL fetched as static HTML (``requests``),
  * a live URL rendered in a headless browser (``selenium``) for pages whose
    content is produced by JavaScript.

Third-party backends are imported lazily so that file/static usage does not
require Selenium to be installed, and vice versa. Every failure mode is raised
as :class:`LoaderError` with an actionable message.
"""

from __future__ import annotations

from pathlib import Path

DEFAULT_TIMEOUT = 30
_USER_AGENT = "section-508-compliance-checker/0.1 (+accessibility audit)"


class LoaderError(Exception):
    """Raised when HTML cannot be acquired from the requested source."""


def load_html(
    *,
    url: str | None = None,
    file: str | None = None,
    render: str = "static",
    timeout: int = DEFAULT_TIMEOUT,
) -> str:
    """Return the HTML for the requested source.

    Exactly one of ``url`` or ``file`` must be provided.
    """
    if file:
        return _load_file(file)
    if url:
        if render == "selenium":
            return _load_selenium(url, timeout)
        return _load_static(url, timeout)
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


def _load_selenium(url: str, timeout: int) -> str:
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
        return driver.page_source
    except WebDriverException as exc:
        raise LoaderError(
            "Selenium could not render the page. Ensure Chrome/Chromium is "
            f"installed and reachable. Underlying error: {exc.msg or exc}"
        ) from exc
    finally:
        if driver is not None:
            driver.quit()
