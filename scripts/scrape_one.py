#!/usr/bin/env python3
"""Scrape one GRE Prep Club question (single fetch, no loops)."""

from __future__ import annotations

import html
import http.cookiejar
import json
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QUESTIONS_FILE = ROOT / "data" / "questions.jsonl"
BASE = "https://gre.myprepclub.com"
USER_AGENT = "gre-practice-bank-scraper/0.1"
LOGIN_URL = f"{BASE}/forum/ucp.php?mode=login"


def load_env(path: Path = ROOT / ".env") -> dict[str, str]:
    env: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            env[key.strip()] = value.strip()
    return env


def make_opener() -> urllib.request.OpenerDirector:
    cookie_jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookie_jar))
    opener.addheaders = [("User-Agent", USER_AGENT)]
    return opener


def fetch(opener: urllib.request.OpenerDirector, url: str) -> str:
    with opener.open(url) as response:
        return response.read().decode("utf-8", errors="replace")


def login(opener: urllib.request.OpenerDirector, username: str, password: str) -> None:
    login_html = fetch(opener, LOGIN_URL)
    data = {
        "username": username,
        "password": password,
        "login": "Login",
        "redirect": "./index.php",
    }
    for name in ("form_token", "sid", "creation_time"):
        match = re.search(rf'name="{name}" value="([^"]+)"', login_html)
        if match:
            data[name] = match.group(1)

    body = urllib.parse.urlencode(data).encode()
    request = urllib.request.Request(LOGIN_URL, data=body, method="POST")
    request.add_header("Content-Type", "application/x-www-form-urlencoded")
    with opener.open(request) as response:
        html_text = response.read().decode("utf-8", errors="replace")

    if "ucp.php?mode=logout" not in html_text:
        raise RuntimeError("login failed: logout link not found in response")


def parse_post_id(url: str) -> str:
    fragment = urllib.parse.urlparse(url).fragment
    if not fragment.startswith("p") or not fragment[1:].isdigit():
        raise ValueError(f"URL fragment must be #p<post_id>, got {url!r}")
    return fragment[1:]


def post_chunk(page_html: str, post_id: str) -> str:
    marker = f'id="p_{post_id}"'
    start = page_html.find(marker)
    if start == -1:
        raise ValueError(f"post wrapper {post_id!r} not found")

    end = page_html.find('<div class="post-wrapper', start + 1)
    if end == -1:
        end = len(page_html)
    return page_html[start:end]


def extract_question_html(chunk: str) -> str:
    text_marker = '<div class="item text">'
    text_start = chunk.find(text_marker)
    if text_start == -1:
        raise ValueError("div.item.text not found in post")

    content_start = text_start + len(text_marker)
    answer_start = chunk.find('<div class="item twoRowsBlock">', content_start)
    signature_start = chunk.find('<div class="post_signature">', content_start)
    stops = [pos for pos in (answer_start, signature_start) if pos != -1]
    content_end = min(stops) if stops else len(chunk)
    return chunk[content_start:content_end].strip()


def extract_official_answer(chunk: str, post_id: str) -> str:
    match = re.search(
        rf'<div id="spoiler_{post_id}" class="downRow">\s*(.*?)\s*</div>',
        chunk,
        re.DOTALL,
    )
    if not match:
        raise ValueError(f"official answer spoiler not found for post {post_id!r}")

    answer = html_to_text(match.group(1))
    if "Official Answer and Stats are available only to registered users" in answer:
        raise RuntimeError("not authenticated: official answer gated behind login")
    return answer.strip()


def html_to_text(fragment: str) -> str:
    text = re.sub(r"<br\s*/?>", "\n", fragment, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def scrape_question(opener: urllib.request.OpenerDirector, source_url: str) -> dict[str, str]:
    post_id = parse_post_id(source_url)
    page_url = source_url.split("#", 1)[0]
    page_html = fetch(opener, page_url)
    chunk = post_chunk(page_html, post_id)
    body_html = extract_question_html(chunk)
    return {
        "source_url": source_url,
        "post_id": post_id,
        "body_html": body_html,
        "body_text": html_to_text(body_html),
        "official_answer": extract_official_answer(chunk, post_id),
    }


def pick_test_url() -> str:
    links = json.loads((ROOT / "data" / "post_links.json").read_text(encoding="utf-8"))
    return links["all_links"][0]


def upsert_question(question: dict[str, str]) -> None:
    questions: dict[str, dict[str, str]] = {}
    if QUESTIONS_FILE.exists():
        for line in QUESTIONS_FILE.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            questions[row["post_id"]] = row
    questions[question["post_id"]] = question
    QUESTIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
    QUESTIONS_FILE.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in questions.values()),
        encoding="utf-8",
    )


def main() -> int:
    source_url = sys.argv[1] if len(sys.argv) > 1 else pick_test_url()
    env = load_env()
    username = env.get("GRE_PREPCLUB_USERNAME")
    password = env.get("GRE_PREPCLUB_PASSWORD")
    if not username or not password:
        print("GRE_PREPCLUB_USERNAME and GRE_PREPCLUB_PASSWORD required in .env", file=sys.stderr)
        return 1

    opener = make_opener()
    login(opener, username, password)
    question = scrape_question(opener, source_url)
    upsert_question(question)
    print(f"wrote line for p{question['post_id']} to {QUESTIONS_FILE.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
