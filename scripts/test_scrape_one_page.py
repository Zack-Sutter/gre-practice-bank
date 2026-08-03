"""Fetch one forum page and extract question links. Single request after login, no loops."""

import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from myprepclub_auth import authenticated_opener, fetch_authenticated

DEFAULT_URL = (
    "https://gre.myprepclub.com/forum/"
    "gre-premium-quant-question-banks-topic-wise-2700-questions-34207.html"
)
QUESTION_LINK_RE = re.compile(r"/forum/gre-[a-z0-9-]+\.html")
OUTPUT_PATH = Path(__file__).resolve().parent.parent / "data" / "test_scrape_one_page.json"


class TitleExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self._in_title = False
        self.parts: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag == "title":
            self._in_title = True

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._in_title:
            self.parts.append(data)


def scrape_one_page(url: str, opener) -> dict:
    html = fetch_authenticated(opener, url)

    title_parser = TitleExtractor()
    title_parser.feed(html)

    question_links = sorted(set(QUESTION_LINK_RE.findall(html)))

    return {
        "source_url": url,
        "authenticated": True,
        "page_title": "".join(title_parser.parts).strip(),
        "html_length": len(html),
        "has_postbody": "postbody" in html.lower(),
        "question_links": question_links,
        "question_link_count": len(question_links),
    }


def main() -> None:
    url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_URL
    opener = authenticated_opener()
    result = scrape_one_page(url, opener)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(result, indent=2))
    print(f"\nWrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
