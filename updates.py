"""Update check: asks GitHub for the newest GamebaseXL release and says whether it is newer than this one.

Nothing is downloaded or installed; the app only tells the user and offers the release page. The request carries
no personal data (a generic User-Agent and the public releases URL). No project imports: easy to test.
"""
import json
import re
import ssl
import threading
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass

REPO = "dimfilhub/GamebaseXL"
API_URL = f"https://api.github.com/repos/{REPO}/releases/latest"
RELEASES_URL = f"https://github.com/{REPO}/releases"
CHECK_INTERVAL = 24 * 3600      # the automatic check runs at most once a day
TIMEOUT = 8                     # seconds; the check never holds the app up


@dataclass(frozen=True)
class Release:
    version: str        # "1.2.0" (no leading v)
    url: str            # the release's web page
    notes: str          # the release description (may be empty)


def parse_version(text: str) -> tuple[int, ...] | None:
    """'v1.2.0' / '1.2' -> (1, 2, 0) / (1, 2); None if it does not start with numbers."""
    match = re.match(r"\s*v?(\d+(?:\.\d+)*)", str(text))
    return tuple(int(part) for part in match.group(1).split(".")) if match else None


def is_newer(latest: str, current: str) -> bool:
    """True if `latest` is a higher version than `current` ('1.2' equals '1.2.0'). Unreadable versions are never newer."""
    a, b = parse_version(latest), parse_version(current)
    if a is None or b is None:
        return False
    size = max(len(a), len(b))
    return a + (0,) * (size - len(a)) > b + (0,) * (size - len(b))


def _ssl_context():
    """Packaged apps often have no system certificates; use certifi's when it is installed."""
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except (ImportError, OSError):
        return None


def fetch_latest(url: str = API_URL, timeout: float = TIMEOUT) -> Release:
    """The newest published release. Raises OSError if GitHub cannot be reached or answers nonsense."""
    request = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json",
                                                   "User-Agent": "GamebaseXL-update-check"})
    try:
        with urllib.request.urlopen(request, timeout=timeout, context=_ssl_context()) as response:
            data = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, ValueError) as error:    # URLError is an OSError; bad JSON is a ValueError
        if isinstance(error, urllib.error.HTTPError):
            error.close()
        raise OSError(str(error)) from error
    tag = data.get("tag_name") if isinstance(data, dict) else None
    if not isinstance(tag, str) or parse_version(tag) is None:
        raise OSError("GitHub's answer has no usable version")
    page = data.get("html_url")
    return Release(version=tag.lstrip("vV"), url=page if isinstance(page, str) and page.startswith("https://") else RELEASES_URL,
                   notes=str(data.get("body") or "").strip())


def due(last_check: float, now: float | None = None) -> bool:
    """True when the automatic check has not run for a day (or the saved time is nonsense)."""
    now = time.time() if now is None else now
    return not 0 <= now - last_check < CHECK_INTERVAL


def check_in_background(on_done: Callable[[Release | None, str | None], None], fetch=fetch_latest) -> threading.Thread:
    """Runs the check on a thread and calls on_done(release, error) from it: the caller hands the result to the
    Tk thread (widget.after). Exactly one of release/error is set."""
    def run():
        try:
            result = (fetch(), None)
        except OSError as error:
            result = (None, str(error) or "no connection")
        on_done(*result)
    thread = threading.Thread(target=run, name="update-check", daemon=True)
    thread.start()
    return thread
