#!/usr/bin/env python3
"""Scrape N unscraped questions with a delay between fetches."""

from __future__ import annotations

import json
import sys
import time

import scrape_one as s

DELAY_SECONDS = 2


def scraped_post_ids() -> set[str]:
    ids: set[str] = set()
    if s.QUESTIONS_FILE.exists():
        for line in s.QUESTIONS_FILE.read_text(encoding="utf-8").splitlines():
            if line.strip():
                ids.add(json.loads(line)["post_id"])
    return ids


def next_urls(count: int) -> list[str]:
    links = json.loads((s.ROOT / "data" / "post_links.json").read_text(encoding="utf-8"))["all_links"]
    scraped = scraped_post_ids()
    urls: list[str] = []
    for url in links:
        if "#p" not in url:
            continue
        if s.parse_post_id(url) in scraped:
            continue
        urls.append(url)
        if len(urls) == count:
            break
    return urls


def main() -> int:
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    urls = next_urls(count)
    if not urls:
        print("no unscraped URLs found", file=sys.stderr)
        return 1

    env = s.load_env()
    opener = s.make_opener()
    s.login(opener, env["GRE_PREPCLUB_USERNAME"], env["GRE_PREPCLUB_PASSWORD"])

    ok, skipped = 0, 0
    for i, url in enumerate(urls):
        if i > 0:
            print(f"waiting {DELAY_SECONDS}s...")
            time.sleep(DELAY_SECONDS)
        try:
            question = s.scrape_question(opener, url)
            s.upsert_question(question)
            ok += 1
            print(f"wrote p{question['post_id']} ({question['official_answer']})")
        except Exception as exc:
            skipped += 1
            post_id = s.parse_post_id(url) if "#p" in url else "?"
            print(f"skipped p{post_id}: {exc}", file=sys.stderr)
    print(f"done: {ok} scraped, {skipped} skipped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
