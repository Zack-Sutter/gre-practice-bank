#!/usr/bin/env python3
"""Extract vocabulary entries from data/word_list.html into data/words.jsonl."""

from __future__ import annotations

import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "word_list.html"
OUTPUT = ROOT / "data" / "words.jsonl"

WORDLIST_RE = re.compile(
    r'<ol class="wordlist[^"]*" id="wordlist">(.*?)</ol>',
    re.DOTALL,
)
ENTRY_RE = re.compile(
    r'<li\b[^>]*\bword="([^"]+)"[^>]*>(.*?)</li>',
    re.DOTALL,
)
DEFINITION_RE = re.compile(
    r'<div class="definition"[^>]*>(.*?)</div>',
    re.DOTALL,
)
EXAMPLE_RE = re.compile(
    r'<div class="example">(.*?)</div>',
    re.DOTALL,
)
TAG_RE = re.compile(r"<[^>]+>")


def strip_html(fragment: str) -> str:
    text = TAG_RE.sub(" ", fragment)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)
    return text.strip()


def extract_entries(page_html: str) -> list[dict[str, str]]:
    wordlist_match = WORDLIST_RE.search(page_html)
    if not wordlist_match:
        raise SystemExit("Could not find #wordlist in HTML")

    entries: list[dict[str, str]] = []
    for word, body in ENTRY_RE.findall(wordlist_match.group(1)):
        definition_match = DEFINITION_RE.search(body)
        definition = strip_html(definition_match.group(1)) if definition_match else ""

        record: dict[str, str] = {"word": word, "definition": definition}

        example_match = EXAMPLE_RE.search(body)
        if example_match:
            example = strip_html(example_match.group(1))
            if example:
                record["example"] = example

        entries.append(record)

    return entries


def main() -> None:
    page_html = SOURCE.read_text(encoding="utf-8")
    entries = extract_entries(page_html)

    with OUTPUT.open("w", encoding="utf-8") as out:
        for entry in entries:
            out.write(json.dumps(entry, ensure_ascii=False) + "\n")

    with_examples = sum(1 for entry in entries if "example" in entry)
    print(f"Wrote {len(entries)} words to {OUTPUT.relative_to(ROOT)}")
    print(f"  {with_examples} with examples, {len(entries) - with_examples} without")


if __name__ == "__main__":
    main()
