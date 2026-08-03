"""Session login for gre.myprepclub.com. Credentials live in .env (gitignored)."""

import os
import re
import urllib.parse
import urllib.request
from http.cookiejar import CookieJar
from pathlib import Path
from urllib.request import HTTPCookieProcessor, Request, build_opener

BASE = "https://gre.myprepclub.com"
USER_AGENT = "gre-practice-bank-scraper/0.1 (educational; github.com/gre-practice-bank)"
REPO_ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = REPO_ROOT / ".env"


def load_env(path: Path = ENV_PATH) -> None:
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, sep, val = line.partition("=")
        if sep:
            os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))


def _request_headers() -> dict[str, str]:
    return {"User-Agent": USER_AGENT}


def make_opener() -> urllib.request.OpenerDirector:
    return build_opener(HTTPCookieProcessor(CookieJar()))


def _fetch(opener: urllib.request.OpenerDirector, url: str, data: bytes | None = None) -> tuple[str, str]:
    headers = _request_headers()
    if data is not None:
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    req = Request(url, data=data, headers=headers, method="POST" if data else "GET")
    with opener.open(req, timeout=30) as resp:
        return resp.read().decode("utf-8", errors="replace"), resp.geturl()


def _logged_in(html: str) -> bool:
    return "logout" in html.lower() or "ucp.php?mode=logout" in html.lower()


def login(
    opener: urllib.request.OpenerDirector,
    username: str,
    password: str,
) -> None:
    login_page_url = f"{BASE}/forum/ucp.php?mode=login"
    html, _ = _fetch(opener, login_page_url)

    sid_match = re.search(r'name="sid"\s+value="([^"]+)"', html)
    sid = sid_match.group(1) if sid_match else ""

    post_url = f"{BASE}/forum/ucp.php?mode=login"
    if sid:
        post_url += f"&sid={urllib.parse.quote(sid)}"

    fields = {
        "username": username,
        "password": password,
        "redirect": "index.php",
        "login": "Login",
    }
    if sid:
        fields["sid"] = sid

    body = urllib.parse.urlencode(fields).encode("utf-8")
    result_html, result_url = _fetch(opener, post_url, body)

    if not _logged_in(result_html):
        lower = result_html.lower()
        if "incorrect" in lower or "password" in lower and "mode=login" in result_url:
            raise RuntimeError("Login failed — check GRE_PREPCLUB_USERNAME and GRE_PREPCLUB_PASSWORD in .env")
        raise RuntimeError(
            "Login may have failed (no logout link in response). "
            "Site may require CAPTCHA — log in in a browser and report the issue."
        )


def authenticated_opener() -> urllib.request.OpenerDirector:
    load_env()
    username = os.environ.get("GRE_PREPCLUB_USERNAME", "").strip()
    password = os.environ.get("GRE_PREPCLUB_PASSWORD", "").strip()

    if not username or not password:
        raise RuntimeError(
            f"Missing credentials. Copy .env.example to {ENV_PATH} and set "
            "GRE_PREPCLUB_USERNAME and GRE_PREPCLUB_PASSWORD."
        )

    opener = make_opener()
    login(opener, username, password)
    return opener


def fetch_authenticated(
    opener: urllib.request.OpenerDirector,
    url: str,
) -> str:
    html, _ = _fetch(opener, url)
    return html
